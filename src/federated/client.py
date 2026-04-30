"""
src/federated/client.py

Flower federated-learning client.

Trains a small 1-D CNN locally on each device's `aegis_local.db`; only
gradient deltas leave the device. Labels are weakly supervised from the
`interpretations.severity_score` column — severity ≥ 5 on the cardiology
specialty is treated as the positive class (anomalous ECG window).

Launch (after `pip install flwr torch`):

    python -m src.federated.client \\
        --server-address 10.0.0.4:8080 \\
        --patient-id medverse-demo-patient
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
from typing import List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import flwr as fl  # type: ignore
    _FLWR_AVAILABLE = True
except Exception:  # pragma: no cover
    _FLWR_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset
    _TORCH_AVAILABLE = True
except Exception:  # pragma: no cover
    _TORCH_AVAILABLE = False


DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "aegis_local.db")
)
WINDOW_LEN = 800  # 20 s @ 40 Hz — matches app.py BUFFER_SIZE defaults


# ─── Real model (replaces the former nn.Linear placeholder) ─────────────────

if _TORCH_AVAILABLE:

    class TinyArrhythmiaModel(nn.Module):
        """
        3-layer 1-D CNN — small enough to train on CPU, deep enough to
        capture QRS morphology after upsampling to 250 Hz.
        """

        def __init__(self, in_len: int = WINDOW_LEN, num_classes: int = 2):
            super().__init__()
            self.conv1 = nn.Conv1d(1, 16, kernel_size=7, padding=3)
            self.conv2 = nn.Conv1d(16, 32, kernel_size=5, padding=2)
            self.conv3 = nn.Conv1d(32, 32, kernel_size=3, padding=1)
            self.pool = nn.MaxPool1d(kernel_size=2)
            self.bn1 = nn.BatchNorm1d(16)
            self.bn2 = nn.BatchNorm1d(32)
            self.bn3 = nn.BatchNorm1d(32)
            pooled = in_len // 8
            self.fc = nn.Linear(32 * pooled, num_classes)

        def forward(self, x):
            x = self.pool(F.relu(self.bn1(self.conv1(x))))
            x = self.pool(F.relu(self.bn2(self.conv2(x))))
            x = self.pool(F.relu(self.bn3(self.conv3(x))))
            x = x.flatten(1)
            return self.fc(x)


# ─── Local data access — real SQLite query ──────────────────────────────────

def load_local_training_set(
    patient_id: str,
    db_path: str = DB_PATH,
    window_len: int = WINDOW_LEN,
    max_rows: int = 5000,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract ECG Lead-II windows + weak labels from the local telemetry DB.

    Strategy:
      • Pull the most recent `max_rows` telemetry snapshots for
        `patient_id` that include a `waveform.ecg_lead2` buffer
        (present when MEDVERSE_INCLUDE_WAVEFORM=true).
      • Label each window with the latest cardiology severity at that
        moment: severity_score ≥ 5 → 1, else 0.
      • Pad / truncate windows to `window_len`.

    Returns (X: float32[N, window_len], y: int64[N]). Empty arrays when
    no usable rows exist (e.g. waveforms were never recorded).
    """
    if not os.path.exists(db_path):
        logger.warning(f"No SQLite db at {db_path} — returning empty training set.")
        return np.zeros((0, window_len), dtype=np.float32), np.zeros((0,), dtype=np.int64)

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.execute(
            """
            SELECT timestamp_str, data
              FROM telemetry
             WHERE patient_id = ?
          ORDER BY id DESC
             LIMIT ?
            """,
            (patient_id, max_rows),
        )
        rows = cur.fetchall()
        # Pull all cardiology interpretations so we can join by time.
        interp_cur = conn.execute(
            """
            SELECT timestamp_str, severity_score
              FROM interpretations
             WHERE patient_id = ?
               AND LOWER(specialty) LIKE '%cardiology%'
          ORDER BY id DESC
            """,
            (patient_id,),
        )
        interps = interp_cur.fetchall()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to read training data: {e}")
        return np.zeros((0, window_len), dtype=np.float32), np.zeros((0,), dtype=np.int64)

    def _label_for(ts_str: str) -> int:
        """Closest-earlier cardiology severity; default 0."""
        if not interps:
            return 0
        for i_ts, score in interps:
            if i_ts and i_ts <= ts_str:
                return 1 if (score or 0.0) >= 5.0 else 0
        return 0

    X: List[np.ndarray] = []
    y: List[int] = []
    for ts_str, blob in rows:
        try:
            snap = json.loads(blob)
            wave = (snap.get("waveform") or {}).get("ecg_lead2") or []
        except Exception:
            continue
        if not wave:
            continue
        arr = np.asarray(wave, dtype=np.float32)
        if len(arr) >= window_len:
            arr = arr[-window_len:]
        else:
            arr = np.pad(arr, (window_len - len(arr), 0), mode="constant")
        X.append(arr)
        y.append(_label_for(ts_str))

    if not X:
        logger.warning(
            "No ECG windows found in aegis_local.db. Turn on "
            "MEDVERSE_INCLUDE_WAVEFORM=true and stream for a while to "
            "populate the training set."
        )
        return np.zeros((0, window_len), dtype=np.float32), np.zeros((0,), dtype=np.int64)

    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.int64)


# ─── Flower client ──────────────────────────────────────────────────────────

if _FLWR_AVAILABLE and _TORCH_AVAILABLE:

    class MedVerseClient(fl.client.NumPyClient):
        def __init__(self, patient_id: str, epochs: int = 1, batch_size: int = 32) -> None:
            self.patient_id = patient_id
            self.epochs = epochs
            self.batch_size = batch_size
            self.device = torch.device("cpu")
            self.model = TinyArrhythmiaModel().to(self.device)
            X, y = load_local_training_set(patient_id)
            if len(X):
                tx = torch.from_numpy(X).unsqueeze(1)  # (N, 1, L)
                ty = torch.from_numpy(y)
                self.loader = DataLoader(TensorDataset(tx, ty), batch_size=batch_size, shuffle=True)
                self.n = int(len(y))
            else:
                self.loader = None
                self.n = 0

        def get_parameters(self, config=None) -> List[np.ndarray]:
            return [p.detach().cpu().numpy() for p in self.model.parameters()]

        def set_parameters(self, parameters: List[np.ndarray]) -> None:
            for tensor, arr in zip(self.model.parameters(), parameters):
                tensor.data = torch.tensor(arr, dtype=tensor.dtype)

        def fit(self, parameters, config):
            self.set_parameters(parameters)
            if not self.loader:
                return self.get_parameters(), 0, {"skipped": "no_data"}
            self.model.train()
            opt = torch.optim.Adam(self.model.parameters(), lr=1e-3)
            loss_fn = nn.CrossEntropyLoss()
            for _ in range(self.epochs):
                for xb, yb in self.loader:
                    opt.zero_grad()
                    logits = self.model(xb)
                    loss = loss_fn(logits, yb)
                    loss.backward()
                    opt.step()
            return self.get_parameters(), self.n, {}

        def evaluate(self, parameters, config):
            self.set_parameters(parameters)
            if not self.loader:
                return 0.0, 0, {"accuracy": 0.0}
            self.model.eval()
            correct = total = 0
            with torch.no_grad():
                for xb, yb in self.loader:
                    logits = self.model(xb)
                    pred = logits.argmax(dim=1)
                    correct += int((pred == yb).sum())
                    total += int(yb.size(0))
            acc = correct / total if total else 0.0
            return 0.0, total, {"accuracy": float(acc)}


def run_client(server_address: str, patient_id: str) -> None:
    if not _FLWR_AVAILABLE:
        raise RuntimeError("flwr not installed. `pip install flwr`")
    if not _TORCH_AVAILABLE:
        raise RuntimeError("torch not installed. `pip install torch`")
    fl.client.start_numpy_client(
        server_address=server_address,
        client=MedVerseClient(patient_id=patient_id),  # type: ignore[arg-type]
    )


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-address", default=os.environ.get("FL_SERVER", "127.0.0.1:8080"))
    parser.add_argument(
        "--patient-id",
        default=os.environ.get("FL_PATIENT_ID", "medverse-demo-patient"),
    )
    args = parser.parse_args()
    run_client(args.server_address, args.patient_id)

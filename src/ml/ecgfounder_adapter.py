"""
src/ml/ecgfounder_adapter.py

Runtime adapter for an ECG rhythm classifier consumed by the cardiology
graph.

  signal = np.asarray(ecg_lead2_buffer, dtype=float)
  adapter = get_ecgfounder()
  if adapter.is_loaded:
      pred = adapter.classify(signal, fs=40)
      # pred → {label, probs, confidence, top_k} appended to tool_results

Originally scaffolded as the ECGFounder PyTorch foundation model
(Liu et al. 2025, 10.7M ECGs, 150-class output). Reimplemented as an
sklearn pickle so it works without dragging torch + a multi-GB weight
download into the HF Space. Same external API; the ECG signal is
reduced to handcraft features (HR, HRV proxy, signal envelope, peak
interval CV) and a RandomForest predicts a clinically-meaningful
subset of ECG findings.

If you want the real ECGFounder weights later, override `classify()`
with a torch path and override `_load_pickle()` to pull a `.pt` —
the call sites in graph_factory.py don't change.

Weight placement:
    models/ecg/ecgfounder/model.pkl
    models/ecg/ecgfounder/labels.txt (optional override)
"""
from __future__ import annotations

import logging
import os
import pickle
from typing import Dict, List, Optional

import numpy as np

from src.ml import MODELS_DIR

logger = logging.getLogger(__name__)

WEIGHTS_SUBPATH = "ecg/ecgfounder/model.pkl"
LABELS_SUBPATH = "ecg/ecgfounder/labels.txt"
DEFAULT_LABELS = [
    "Sinus Rhythm",
    "Atrial Fibrillation",
    "Premature Atrial Contraction",
    "Premature Ventricular Contraction",
    "ST Elevation",
    "ST Depression",
    "Bundle Branch Block",
    "Other",
]


def _extract_features(signal: np.ndarray, fs: int) -> Dict[str, float]:
    """Match the feature set the pickle was trained on. Anything we
    can't compute returns 0.0 — the trained imputer covers it."""
    s = np.asarray(signal, dtype=float)
    if s.size == 0:
        return {
            "duration_s": 0.0, "hr_estimate": 0.0, "hrv_proxy": 0.0,
            "signal_rms": 0.0, "p95_p05_range": 0.0, "peak_interval_cv": 0.0,
        }
    duration_s = float(s.size / max(fs, 1))
    rms = float(np.sqrt(np.mean(s * s)))
    p95 = float(np.percentile(s, 95))
    p05 = float(np.percentile(s, 5))
    p_range = p95 - p05

    # Crude QRS detection: peaks above (mean + 0.6 × std), spaced ≥0.3 s
    if s.size < int(fs * 0.6):
        return {
            "duration_s": duration_s, "hr_estimate": 0.0, "hrv_proxy": 0.0,
            "signal_rms": rms, "p95_p05_range": p_range, "peak_interval_cv": 0.0,
        }
    threshold = float(np.mean(s) + 0.6 * np.std(s))
    min_distance = max(int(fs * 0.3), 1)
    peaks: List[int] = []
    last_peak = -min_distance
    for i in range(1, s.size - 1):
        if s[i] > threshold and s[i] > s[i - 1] and s[i] >= s[i + 1] and i - last_peak >= min_distance:
            peaks.append(i)
            last_peak = i

    if len(peaks) < 2:
        return {
            "duration_s": duration_s, "hr_estimate": 0.0, "hrv_proxy": 0.0,
            "signal_rms": rms, "p95_p05_range": p_range, "peak_interval_cv": 0.0,
        }
    intervals = np.diff(peaks) / float(fs)  # seconds between R-peaks
    hr = 60.0 / float(np.mean(intervals)) if np.mean(intervals) > 0 else 0.0
    hrv_proxy = float(np.std(intervals) * 1000.0)  # ms
    interval_cv = float(np.std(intervals) / np.mean(intervals)) if np.mean(intervals) > 0 else 0.0
    return {
        "duration_s": duration_s,
        "hr_estimate": hr,
        "hrv_proxy": hrv_proxy,
        "signal_rms": rms,
        "p95_p05_range": p_range,
        "peak_interval_cv": interval_cv,
    }


class ECGFounderAdapter:
    """Stateful singleton wrapper around the ECG classifier."""

    def __init__(self) -> None:
        self._preprocessor = None
        self._model = None
        self._labels: List[str] = list(DEFAULT_LABELS)
        self.is_loaded: bool = False
        self.weights_path: str = os.path.join(MODELS_DIR, WEIGHTS_SUBPATH)
        self.labels_path: str = os.path.join(MODELS_DIR, LABELS_SUBPATH)

    # ── loading ────────────────────────────────────────────────────────

    def load(self) -> bool:
        if self.is_loaded:
            return True
        if not os.path.exists(self.weights_path):
            logger.info(
                f"ECGFounder pickle not found at {self.weights_path} — "
                "cardiology graph will fall back to LLM-only ECG reading."
            )
            return False
        try:
            self._load_labels()
            with open(self.weights_path, "rb") as f:
                payload = pickle.load(f)
            self._preprocessor = payload.get("preprocessor")
            self._model = payload.get("model")
            self.is_loaded = self._model is not None
            if self.is_loaded:
                model_classes = list(getattr(self._model, "classes_", []))
                if model_classes:
                    self._labels = [str(c) for c in model_classes]
                logger.info(f"ECGFounder loaded (labels={self._labels}).")
            return self.is_loaded
        except Exception as e:
            logger.warning(f"ECGFounder load failed: {e}")
            return False

    def _load_labels(self) -> None:
        if os.path.exists(self.labels_path):
            try:
                with open(self.labels_path, "r", encoding="utf-8") as fh:
                    self._labels = [line.strip() for line in fh if line.strip()] or DEFAULT_LABELS
            except Exception:
                pass

    # ── inference ──────────────────────────────────────────────────────

    def classify(self, signal: np.ndarray, fs: int = 40) -> Optional[Dict]:
        """Return {label, probs, confidence, top_k}. None if not loaded."""
        if not self.is_loaded:
            return None
        try:
            import pandas as pd
            row = _extract_features(signal, fs)
            df = pd.DataFrame([row])
            x = self._preprocessor.transform(df) if self._preprocessor is not None else df.values
            label = str(self._model.predict(x)[0])
            out: Dict = {"label": label}
            if hasattr(self._model, "predict_proba"):
                probs_arr = self._model.predict_proba(x)[0]
                probs = {str(c): float(p) for c, p in zip(self._labels, probs_arr)}
                out["probs"] = probs
                out["confidence"] = float(max(probs_arr))
                # Top-3 most likely findings
                ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
                out["top_k"] = [{"label": k, "prob": v} for k, v in ranked[:3]]
            return out
        except Exception as e:
            logger.warning(f"ECGFounder classify failed: {e}")
            return None

    def embed(self, signal: np.ndarray, fs: int = 40) -> Optional[np.ndarray]:
        """Return a small (D,) embedding of the ECG window — the
        feature vector itself, repurposed as an embedding so downstream
        callers (RAG, similarity search) can index ECG windows even
        without a real foundation model."""
        if not self.is_loaded:
            return None
        try:
            row = _extract_features(signal, fs)
            return np.asarray(list(row.values()), dtype=float)
        except Exception:
            return None


_singleton: Optional[ECGFounderAdapter] = None


def get_ecgfounder() -> ECGFounderAdapter:
    """Return (and lazily load) the shared ECGFounder adapter."""
    global _singleton
    if _singleton is None:
        _singleton = ECGFounderAdapter()
        _singleton.load()
    return _singleton

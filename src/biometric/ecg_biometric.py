"""
src/biometric/ecg_biometric.py

ECG-based passive biometric identity — a Siamese embedding network that
learns each patient's cardiac signature from their first 24 h of ECG
and then (a) recognises them automatically across sessions and
(b) detects drift from their *personalised* baseline.

Stored anchors live in the existing Chroma `cardiology_history` collection
under metadata `{"type": "biometric_anchor", "patient_id": <id>}` — no
new persistence needed.

This file is a scaffold: `_load_model()` loads a user-supplied Siamese
encoder (output dimension D, cosine-similarity scoring). All public
methods are safe to call before the model is ready; they return None
or `"unknown"` so upstream code never crashes.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from src.ml import MODELS_DIR

logger = logging.getLogger(__name__)

WEIGHTS_SUBPATH = "ecg/biometric_siamese/weights.pt"
ANCHOR_THRESHOLD = float(os.environ.get("MEDVERSE_BIOMETRIC_THRESHOLD", "0.75"))


@dataclass
class BiometricMatch:
    patient_id: str
    score: float
    matched: bool


class ECGBiometric:
    def __init__(self) -> None:
        self._encoder = None
        self.is_loaded: bool = False
        self.weights_path: str = os.path.join(MODELS_DIR, WEIGHTS_SUBPATH)

    def load(self) -> bool:
        if self.is_loaded:
            return True
        if not os.path.exists(self.weights_path):
            logger.info(
                f"ECG biometric weights not found at {self.weights_path} — "
                "biometric identification disabled."
            )
            return False
        try:
            self._load_model()
            self.is_loaded = True
            logger.info("ECG biometric encoder loaded.")
            return True
        except Exception as e:
            logger.warning(f"Biometric encoder load failed: {e}")
            return False

    def _load_model(self) -> None:
        raise NotImplementedError(
            "Plug in a Siamese encoder here. See models/ecg/biometric_siamese/README.md"
        )

    # ── embedding / scoring ───────────────────────────────────────────

    def embed(self, ecg_window: np.ndarray) -> Optional[np.ndarray]:
        if not self.is_loaded:
            return None
        return None  # Placeholder — call self._encoder on ecg_window.

    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    # ── public API ────────────────────────────────────────────────────

    def enroll(self, patient_id: str, ecg_windows: List[np.ndarray]) -> Optional[np.ndarray]:
        """
        Learn a personalised anchor embedding from ≥N clean ECG windows.
        Returns the mean embedding (caller persists it — e.g. into Chroma).
        """
        if not self.is_loaded or not ecg_windows:
            return None
        embeddings = [self.embed(w) for w in ecg_windows]
        embeddings = [e for e in embeddings if e is not None]
        if not embeddings:
            return None
        return np.mean(np.stack(embeddings, axis=0), axis=0)

    def identify(
        self,
        ecg_window: np.ndarray,
        anchors: List[Tuple[str, np.ndarray]],
        threshold: float = ANCHOR_THRESHOLD,
    ) -> BiometricMatch:
        """
        Compare a live ECG window against stored anchors.
        Returns the best-matching patient + cosine score; `matched=False`
        if nothing exceeds the threshold.
        """
        emb = self.embed(ecg_window)
        if emb is None or not anchors:
            return BiometricMatch(patient_id="unknown", score=0.0, matched=False)
        scored = [(pid, self.cosine(emb, anchor)) for pid, anchor in anchors]
        scored.sort(key=lambda x: x[1], reverse=True)
        best_id, best_score = scored[0]
        return BiometricMatch(
            patient_id=best_id,
            score=best_score,
            matched=best_score >= threshold,
        )


_singleton: Optional[ECGBiometric] = None


def get_ecg_biometric() -> ECGBiometric:
    global _singleton
    if _singleton is None:
        _singleton = ECGBiometric()
        _singleton.load()
    return _singleton

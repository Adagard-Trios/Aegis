"""
src/ml/ecgfounder_adapter.py

Runtime adapter for the ECGFounder foundation model (Liu et al., 2025;
PubMed 40771651). ECGFounder is trained on 10.7M ECGs and provides
embeddings + multi-label classification across 150 cardiac diagnoses.

Intended flow inside the cardiology graph:

    signal = np.asarray(ecg_lead2_buffer, dtype=float)
    adapter = get_ecgfounder()
    if adapter.is_loaded:
        pred = adapter.classify(signal, fs=40)
        emb  = adapter.embed(signal, fs=40)
        # → feed `pred` + `emb` into the LLM prompt as structured context

Weight placement:
    models/ecg/ecgfounder/<weights>.pt  (see README.md § ML pipelines)

This file is a scaffold. `load()` returns False until real weights are
placed and `_load_weights()` is implemented by the user (typical stack:
PyTorch + 1D-CNN, see the ECGFounder paper supplementary for the exact
architecture).
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

import numpy as np

from src.ml import MODELS_DIR

logger = logging.getLogger(__name__)

WEIGHTS_SUBPATH = "ecg/ecgfounder/weights.pt"
LABELS_SUBPATH = "ecg/ecgfounder/labels.txt"


class ECGFounderAdapter:
    """Stateful singleton wrapper around the ECGFounder network."""

    def __init__(self) -> None:
        self._model = None
        self._labels: List[str] = []
        self.is_loaded: bool = False
        self.weights_path: str = os.path.join(MODELS_DIR, WEIGHTS_SUBPATH)
        self.labels_path: str = os.path.join(MODELS_DIR, LABELS_SUBPATH)

    # ── loading ────────────────────────────────────────────────────────

    def load(self) -> bool:
        if self.is_loaded:
            return True
        if not os.path.exists(self.weights_path):
            logger.info(
                f"ECGFounder weights not found at {self.weights_path} — "
                "cardiology graph will fall back to LLM-only classification."
            )
            return False
        try:
            self._load_weights()
            self._load_labels()
            self.is_loaded = True
            logger.info("ECGFounder weights loaded.")
            return True
        except Exception as e:
            logger.warning(f"ECGFounder load failed: {e}")
            return False

    def _load_weights(self) -> None:
        """Override with: torch.load(self.weights_path, map_location='cpu')."""
        raise NotImplementedError(
            "Plug in a PyTorch model here. See models/ecg/ecgfounder/README.md"
        )

    def _load_labels(self) -> None:
        if os.path.exists(self.labels_path):
            with open(self.labels_path, "r", encoding="utf-8") as fh:
                self._labels = [line.strip() for line in fh if line.strip()]

    # ── inference ──────────────────────────────────────────────────────

    def classify(self, signal: np.ndarray, fs: int = 40) -> Optional[dict]:
        """Return {label, auroc, top_k: [...]}. None if not loaded."""
        if not self.is_loaded:
            return None
        # Implementation placeholder — wire up to self._model when weights land.
        return None

    def embed(self, signal: np.ndarray, fs: int = 40) -> Optional[np.ndarray]:
        """Return an (D,) embedding for the ECG window. None if not loaded."""
        if not self.is_loaded:
            return None
        return None


_singleton: Optional[ECGFounderAdapter] = None


def get_ecgfounder() -> ECGFounderAdapter:
    """Return (and lazily load) the shared ECGFounder adapter."""
    global _singleton
    if _singleton is None:
        _singleton = ECGFounderAdapter()
        _singleton.load()
    return _singleton

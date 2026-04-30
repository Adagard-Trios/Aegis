"""
src/ml/pulmonary_classifier.py

Runtime adapter for a respiratory-sound CNN fine-tuned on the ICBHI 2017
Respiratory Sound Database (4 classes: normal / wheeze / crackle / stridor).

Intended flow inside the pulmonary graph:

    audio_window = np.asarray(i2s_audio_buffer, dtype=float)
    clf = get_pulmonary_classifier()
    if clf.is_loaded:
        pred = clf.predict(audio_window, fs=40)
        # → attach pred.label + pred.probs to the pulmonary LLM prompt

Weight placement:
    models/pulmonary/icbhi_cnn/<weights>.pt
    models/pulmonary/icbhi_cnn/class_names.json

Scaffold — `_load_weights()` is user-supplied. Suggested architecture:
mel-spectrogram input (64 mel bins, 3-second window, hop 10 ms) → small
EfficientNet-B0 or ResNet-18 → 4-way softmax.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from src.ml import MODELS_DIR

logger = logging.getLogger(__name__)

WEIGHTS_SUBPATH = "pulmonary/icbhi_cnn/weights.pt"
CLASSES_SUBPATH = "pulmonary/icbhi_cnn/class_names.json"
DEFAULT_CLASSES = ["normal", "wheeze", "crackle", "stridor"]


@dataclass
class RespiratoryPrediction:
    label: str
    probs: Dict[str, float]
    confidence: float


class RespiratorySoundClassifier:
    def __init__(self) -> None:
        self._model = None
        self.classes: List[str] = list(DEFAULT_CLASSES)
        self.is_loaded: bool = False
        self.weights_path: str = os.path.join(MODELS_DIR, WEIGHTS_SUBPATH)
        self.classes_path: str = os.path.join(MODELS_DIR, CLASSES_SUBPATH)

    def load(self) -> bool:
        if self.is_loaded:
            return True
        if not os.path.exists(self.weights_path):
            logger.info(
                f"Respiratory-sound CNN weights not found at {self.weights_path} — "
                "pulmonary graph will fall back to RMS-only features."
            )
            return False
        try:
            self._load_classes()
            self._load_weights()
            self.is_loaded = True
            logger.info("Respiratory-sound CNN loaded.")
            return True
        except Exception as e:
            logger.warning(f"Respiratory CNN load failed: {e}")
            return False

    def _load_classes(self) -> None:
        if os.path.exists(self.classes_path):
            with open(self.classes_path, "r", encoding="utf-8") as fh:
                self.classes = json.load(fh) or DEFAULT_CLASSES

    def _load_weights(self) -> None:
        raise NotImplementedError(
            "Plug in a PyTorch model here. See models/pulmonary/icbhi_cnn/README.md"
        )

    # ── inference ─────────────────────────────────────────────────────

    def predict(self, audio_window: np.ndarray, fs: int = 40) -> Optional[RespiratoryPrediction]:
        if not self.is_loaded:
            return None
        # Placeholder — call self._model on a mel-spectrogram of audio_window.
        return None


_singleton: Optional[RespiratorySoundClassifier] = None


def get_pulmonary_classifier() -> RespiratorySoundClassifier:
    global _singleton
    if _singleton is None:
        _singleton = RespiratorySoundClassifier()
        _singleton.load()
    return _singleton

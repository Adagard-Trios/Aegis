"""
src/ml/pulmonary_classifier.py

Runtime adapter for a respiratory-sound classifier consumed by the
pulmonary graph.

  audio_window = np.asarray(i2s_audio_buffer, dtype=float)
  clf = get_pulmonary_classifier()
  if clf.is_loaded:
      pred = clf.predict(audio_window, fs=40)
      # → attach pred.label + pred.probs to the pulmonary LLM prompt

Originally scaffolded as a PyTorch CNN (mel-spectrogram → ResNet-18).
Reimplemented as a sklearn pickle so it works without dragging torch +
torchaudio + a GPU runtime into the HF Space (~700 MB delta + slow
CPU inference). Same external API; the signal is reduced to handcraft
features (RMS, ZCR, p95/p05 envelope, duration) and a RandomForest
predicts the class.

Weight placement:
    models/pulmonary/icbhi_cnn/model.pkl
    models/pulmonary/icbhi_cnn/class_names.json (optional override)
"""
from __future__ import annotations

import json
import logging
import os
import pickle
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from src.ml import MODELS_DIR

logger = logging.getLogger(__name__)

WEIGHTS_SUBPATH = "pulmonary/icbhi_cnn/model.pkl"
CLASSES_SUBPATH = "pulmonary/icbhi_cnn/class_names.json"
DEFAULT_CLASSES = ["normal", "wheeze", "crackle", "stridor"]


@dataclass
class RespiratoryPrediction:
    label: str
    probs: Dict[str, float]
    confidence: float


def _extract_features(audio_window: np.ndarray, fs: int) -> Dict[str, float]:
    """Match the feature set the pickle was trained on. Anything we
    can't compute returns 0.0 — the trained imputer covers it."""
    a = np.asarray(audio_window, dtype=float)
    if a.size == 0:
        return {"duration_s": 0.0, "rms": 0.0, "zcr": 0.0, "p95": 0.0, "p05": 0.0}
    duration_s = float(a.size / max(fs, 1))
    rms = float(np.sqrt(np.mean(a * a)))
    # Zero-crossing rate (sign changes / sample)
    signs = np.sign(a)
    signs[signs == 0] = 1
    zcr = float(np.mean(np.abs(np.diff(signs)) > 0))
    p95 = float(np.percentile(a, 95))
    p05 = float(np.percentile(a, 5))
    return {"duration_s": duration_s, "rms": rms, "zcr": zcr, "p95": p95, "p05": p05}


class RespiratorySoundClassifier:
    def __init__(self) -> None:
        self._preprocessor = None
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
                f"Pulmonary classifier pickle not found at {self.weights_path} — "
                "pulmonary graph will fall back to RMS-only features."
            )
            return False
        try:
            self._load_classes()
            with open(self.weights_path, "rb") as f:
                payload = pickle.load(f)
            # Same {preprocessor, model} dict shape as PickledTabularAdapter
            self._preprocessor = payload.get("preprocessor")
            self._model = payload.get("model")
            self.is_loaded = self._model is not None
            if self.is_loaded:
                # Prefer the model's own class order over the JSON fallback
                model_classes = list(getattr(self._model, "classes_", []))
                if model_classes:
                    self.classes = [str(c) for c in model_classes]
                logger.info(f"Pulmonary classifier loaded (classes={self.classes}).")
            return self.is_loaded
        except Exception as e:
            logger.warning(f"Pulmonary classifier load failed: {e}")
            return False

    def _load_classes(self) -> None:
        if os.path.exists(self.classes_path):
            try:
                with open(self.classes_path, "r", encoding="utf-8") as fh:
                    self.classes = json.load(fh) or DEFAULT_CLASSES
            except Exception:
                pass

    # ── inference ─────────────────────────────────────────────────────

    def predict(self, audio_window: np.ndarray, fs: int = 40) -> Optional[RespiratoryPrediction]:
        if not self.is_loaded:
            return None
        try:
            import pandas as pd
            row = _extract_features(audio_window, fs)
            df = pd.DataFrame([row])
            x = self._preprocessor.transform(df) if self._preprocessor is not None else df.values
            label = str(self._model.predict(x)[0])
            probs_arr = self._model.predict_proba(x)[0] if hasattr(self._model, "predict_proba") else None
            if probs_arr is not None:
                probs = {str(c): float(p) for c, p in zip(self.classes, probs_arr)}
                confidence = float(max(probs_arr))
            else:
                probs = {label: 1.0}
                confidence = 1.0
            return RespiratoryPrediction(label=label, probs=probs, confidence=confidence)
        except Exception as e:
            logger.warning(f"Pulmonary predict failed: {e}")
            return None


_singleton: Optional[RespiratorySoundClassifier] = None


def get_pulmonary_classifier() -> RespiratorySoundClassifier:
    global _singleton
    if _singleton is None:
        _singleton = RespiratorySoundClassifier()
        _singleton.load()
    return _singleton

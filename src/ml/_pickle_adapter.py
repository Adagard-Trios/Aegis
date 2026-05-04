"""
Tiny shared base for pickle-loaded sklearn adapters.

The 12 training pipelines under models/<slug>/ each save a `ModelEstimator
(preprocessor + sklearn model)` pickle. The estimator class lives inside
each pipeline's namespace, so we can't unpickle it directly from
src/ml/*.py — different `src.` resolution. Each pipeline's
`export_runtime.py` therefore extracts the preprocessor + model from the
ModelEstimator and re-saves them as a plain dict, which any process can
load with stdlib pickle.

This base loads that runtime dict, tracks `is_loaded`, and exposes a
`predict_dict()` helper so the per-pipeline adapter just declares its
weights subpath + `_to_features()` mapping from the live telemetry into
a numpy row.
"""
from __future__ import annotations

import logging
import os
import pickle
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from src.ml import MODELS_DIR

logger = logging.getLogger(__name__)


class PickledTabularAdapter:
    """Base for tabular sklearn adapters loaded from a runtime pickle dict.

    Subclasses set:
      WEIGHTS_SUBPATH:  relative to MODELS_DIR, e.g. "obstetrics/fetal_health/model.pkl"
      DOMAIN_LABEL:     short tag used in log messages
      LABELS:           optional ordered list mapping class index -> name

    And override:
      _to_feature_row(input_dict) -> dict of feature_name -> value
        Returns the columns the trained preprocessor expects. The base
        wraps the dict in a 1-row DataFrame and runs preprocessor +
        model end-to-end.
    """

    WEIGHTS_SUBPATH: str = ""
    DOMAIN_LABEL: str = "<base>"
    LABELS: Optional[list] = None

    def __init__(self) -> None:
        self._preprocessor = None
        self._model = None
        self.is_loaded: bool = False
        self.weights_path: str = os.path.join(MODELS_DIR, self.WEIGHTS_SUBPATH)

    # ── loading ────────────────────────────────────────────────────────

    def load(self) -> bool:
        if self.is_loaded:
            return True
        if not self.WEIGHTS_SUBPATH:
            logger.warning(f"{self.DOMAIN_LABEL}: WEIGHTS_SUBPATH not set")
            return False
        if not os.path.exists(self.weights_path):
            logger.info(
                f"{self.DOMAIN_LABEL} weights not found at {self.weights_path} - "
                "graph will fall back to LLM-only assessment."
            )
            return False
        try:
            with open(self.weights_path, "rb") as fh:
                bundle = pickle.load(fh)
            self._preprocessor = bundle.get("preprocessor")
            self._model = bundle.get("model")
            if self._model is None:
                logger.warning(f"{self.DOMAIN_LABEL}: pickle missing 'model' key")
                return False
            self.is_loaded = True
            logger.info(f"{self.DOMAIN_LABEL} runtime model loaded.")
            return True
        except Exception as e:
            logger.warning(f"{self.DOMAIN_LABEL} load failed: {e}")
            return False

    # ── inference ──────────────────────────────────────────────────────

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Map live telemetry into the feature columns the trained
        preprocessor expects. Override per pipeline."""
        raise NotImplementedError

    def predict_dict(self, input_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run preprocessor + model on a single feature row.

        Returns a JSON-serialisable dict with at minimum {label, confidence};
        adds {probs} when the model exposes predict_proba. Returns None
        when not loaded or on inference error (we never raise from here —
        the calling node should degrade silently)."""
        if not self.is_loaded:
            return None
        try:
            row = self._to_feature_row(input_dict)
            if not row:
                return None
            df = pd.DataFrame([row])
            x = self._preprocessor.transform(df) if self._preprocessor is not None else df.values
            return self._predict_array(x)
        except Exception as e:
            logger.warning(f"{self.DOMAIN_LABEL} predict failed: {e}")
            return None

    def predict_array(self, x: np.ndarray) -> Optional[Dict[str, Any]]:
        """Run preprocessor + model on a pre-shaped feature array.

        Used by image / signal adapters that build their own feature
        vector and don't fit the dict-row pattern."""
        if not self.is_loaded:
            return None
        try:
            if self._preprocessor is not None and x.ndim == 2:
                x = self._preprocessor.transform(x)
            return self._predict_array(x)
        except Exception as e:
            logger.warning(f"{self.DOMAIN_LABEL} predict failed: {e}")
            return None

    def _predict_array(self, x) -> Dict[str, Any]:
        """Shared post-transform path: predict, optionally predict_proba,
        format as a JSON-friendly dict."""
        pred = self._model.predict(x)
        out: Dict[str, Any] = {}
        # Single-row input → scalar output
        first = pred[0] if hasattr(pred, "__len__") and len(pred) > 0 else pred

        if self.LABELS and isinstance(first, (int, np.integer)) and 0 <= int(first) < len(self.LABELS):
            out["label"] = self.LABELS[int(first)]
            out["class_index"] = int(first)
        elif isinstance(first, (int, np.integer, str)):
            out["label"] = str(first)
        else:
            # Regression result
            out["value"] = float(first)
            out["label"] = f"{float(first):.2f}"

        if hasattr(self._model, "predict_proba"):
            try:
                probs = self._model.predict_proba(x)[0]
                if self.LABELS and len(self.LABELS) == len(probs):
                    out["probs"] = {self.LABELS[i]: float(p) for i, p in enumerate(probs)}
                else:
                    out["probs"] = {f"class_{i}": float(p) for i, p in enumerate(probs)}
                out["confidence"] = float(max(probs))
            except Exception:
                pass
        return out

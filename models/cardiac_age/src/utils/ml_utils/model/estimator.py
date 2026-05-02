"""Bundles a fitted preprocessor + a fitted model so they can be persisted
and loaded as one artifact at inference time."""
from __future__ import annotations

import sys
from typing import Any

from src.exception.exception import MedVerseException


class ModelEstimator:
    def __init__(self, preprocessor: Any, model: Any):
        self.preprocessor = preprocessor
        self.model = model

    def predict(self, x):
        try:
            x_t = self.preprocessor.transform(x) if self.preprocessor is not None else x
            return self.model.predict(x_t)
        except Exception as e:
            raise MedVerseException(e, sys) from e

    def predict_proba(self, x):
        try:
            x_t = self.preprocessor.transform(x) if self.preprocessor is not None else x
            if hasattr(self.model, "predict_proba"):
                return self.model.predict_proba(x_t)
            raise AttributeError("Underlying model has no predict_proba")
        except Exception as e:
            raise MedVerseException(e, sys) from e

"""
Runtime adapter for the stress_ans pipeline (WESAD-style synthetic
features + MLPClassifier baseline; 3-class baseline / stress / amusement).

Maps the live vitals snapshot's HR / HRV / breathing-rate / temperature
into the 7 features the model expects. The vest doesn't have an EDA
sensor, so eda_mean / eda_peaks are left None — the trained
preprocessor's median-imputer covers them. The neurology + general-
physician graphs both consume this for autonomic-state context.

Weight placement: models/neurology/stress_ans/model.pkl
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.ml._pickle_adapter import PickledTabularAdapter

logger = logging.getLogger(__name__)


class StressANSAdapter(PickledTabularAdapter):
    WEIGHTS_SUBPATH = "neurology/stress_ans/model.pkl"
    DOMAIN_LABEL = "stress_ans"
    LABELS = ["baseline", "stress", "amusement"]

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        if not input_dict:
            return {}
        vitals = input_dict.get("vitals") if isinstance(input_dict.get("vitals"), dict) else {}
        temp = input_dict.get("temperature") if isinstance(input_dict.get("temperature"), dict) else {}
        return {
            "hr_mean": vitals.get("heart_rate"),
            "hr_std": None,                           # would come from a windowed analyser
            "hrv_rmssd": vitals.get("hrv_rmssd"),
            "br_mean": vitals.get("breathing_rate"),
            "eda_mean": None,                         # no EDA sensor on this vest
            "eda_peaks": None,
            "temp_mean": temp.get("cervical"),
        }


_singleton: Optional[StressANSAdapter] = None


def get_stress_ans() -> StressANSAdapter:
    global _singleton
    if _singleton is None:
        _singleton = StressANSAdapter()
        _singleton.load()
    return _singleton

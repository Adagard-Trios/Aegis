"""
Runtime adapter for the ecg_arrhythmia pipeline (PTB-XL,
GradientBoostingClassifier baseline).

Today's pipeline trains on PTB-XL metadata + per-record presence flags
(age, sex, has_norm, has_mi, has_sttc) and predicts the dominant
diagnostic class. The runtime adapter maps the live snapshot's patient
demographics + simple vital-derived flags into those features. Once the
ECGFounder runtime weights land, this adapter complements (not replaces)
ECGFounderAdapter — both can run side-by-side and the LLM gets two
independent classifications to reason against.

Weight placement: models/cardiology/ecg_arrhythmia/model.pkl
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.ml._pickle_adapter import PickledTabularAdapter

logger = logging.getLogger(__name__)


class ECGArrhythmiaAdapter(PickledTabularAdapter):
    WEIGHTS_SUBPATH = "cardiology/ecg_arrhythmia/model.pkl"
    DOMAIN_LABEL = "ecg_arrhythmia"
    # PTB-XL diagnostic super-classes
    LABELS = ["NORM", "MI", "STTC", "CD", "HYP"]

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        if not input_dict:
            return {}
        patient = input_dict.get("patient") if isinstance(input_dict.get("patient"), dict) else {}
        vitals = input_dict.get("vitals") if isinstance(input_dict.get("vitals"), dict) else {}
        sex = (patient.get("sex") or "").strip().lower()
        # has_* flags are weak heuristics from live vitals — the trained
        # preprocessor median-imputes anything we can't supply.
        hr = vitals.get("heart_rate") or 0
        hrv = vitals.get("hrv_rmssd") or 50
        return {
            "age": patient.get("age"),
            "sex": 1 if sex.startswith("m") else 0,
            "has_norm": 1 if (60 <= hr <= 100 and hrv >= 25) else 0,
            "has_mi": 0,    # would come from ST-segment analyser when available
            "has_sttc": 1 if hrv < 15 else 0,
        }


_singleton: Optional[ECGArrhythmiaAdapter] = None


def get_ecg_arrhythmia() -> ECGArrhythmiaAdapter:
    global _singleton
    if _singleton is None:
        _singleton = ECGArrhythmiaAdapter()
        _singleton.load()
    return _singleton

"""
Runtime adapter for the cardiac_age pipeline (PTB-XL,
GradientBoostingRegressor predicting biological age in years).

The headline output is the **cardiac-age delta** (biological vs
chronological), mirroring retinal_age. Positive delta = accelerated
cardiac aging — a signal worth surfacing into the cardiology graph
even when the LLM's primary findings are otherwise normal.

Weight placement: models/cardiology/cardiac_age/model.pkl
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.ml._pickle_adapter import PickledTabularAdapter

logger = logging.getLogger(__name__)


class CardiacAgeAdapter(PickledTabularAdapter):
    WEIGHTS_SUBPATH = "cardiology/cardiac_age/model.pkl"
    DOMAIN_LABEL = "cardiac_age"
    # Regression — no LABELS; the base returns a `value` field

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        if not input_dict:
            return {}
        patient = input_dict.get("patient") if isinstance(input_dict.get("patient"), dict) else {}
        sex = (patient.get("sex") or "").strip().lower()
        return {
            "sex": 1 if sex.startswith("m") else 0,
            "heart_axis_left": 0,    # would come from a 12-lead axis estimator
            "heart_axis_right": 0,
        }

    def predict_with_chrono(self, snapshot_or_demo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Same shape as retinal_age.predict_with_image — adds a delta
        field when chronological age is present."""
        base = self.predict_dict(snapshot_or_demo or {})
        if base is None:
            return None
        bio_age = base.get("value")
        if bio_age is None:
            return None
        out: Dict[str, Any] = {"biological_age": float(bio_age)}
        patient = snapshot_or_demo.get("patient") if isinstance(snapshot_or_demo.get("patient"), dict) else {}
        chrono = patient.get("age")
        if isinstance(chrono, (int, float)) and chrono > 0:
            delta = float(bio_age) - float(chrono)
            out["chronological_age"] = float(chrono)
            out["delta_years"] = round(delta, 1)
            out["accelerated"] = delta > 5.0
            out["label"] = f"Cardiac age {bio_age:.1f}y vs chrono {chrono:.0f}y (Δ {delta:+.1f}y)"
        else:
            out["label"] = f"Cardiac age {bio_age:.1f}y (no chrono for delta)"
        return out


_singleton: Optional[CardiacAgeAdapter] = None


def get_cardiac_age() -> CardiacAgeAdapter:
    global _singleton
    if _singleton is None:
        _singleton = CardiacAgeAdapter()
        _singleton.load()
    return _singleton

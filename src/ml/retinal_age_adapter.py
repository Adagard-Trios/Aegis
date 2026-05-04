"""
Runtime adapter for the retinal_age pipeline (ODIR + RETFound MAE
regression to biological age in years).

Today's pipeline trains on metadata features (sex, age target,
image_path) — the full RETFound MAE ViT-Large encoder is a follow-up
upgrade. The runtime adapter exposes an image-aware contract so the UI
can already pass uploaded fundus images through; the underlying model
currently only consumes sex (image_path is recorded on the response).

The headline output the agent layer cares about is **retinal-age delta**
— biological_age vs chronological_age. A positive delta indicates
accelerated retinal aging (potential systemic vascular risk).

Weight placement:
    models/ocular/retinal_age/model.pkl  (produced by
    `python models/retinal_age/export_runtime.py`)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.ml._pickle_adapter import PickledTabularAdapter

logger = logging.getLogger(__name__)


class RetinalAgeAdapter(PickledTabularAdapter):
    WEIGHTS_SUBPATH = "ocular/retinal_age/model.pkl"
    DOMAIN_LABEL = "retinal_age"
    # No LABELS — this is regression. The base class returns a `value`
    # field which we wrap with delta computation in predict_with_image.

    _FEATURES = ["sex_male"]   # ODIR sex; image-derived features come later

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        if not input_dict:
            return {}
        sex = (input_dict.get("sex") or "").strip().lower()
        return {"sex_male": 1 if sex.startswith("m") else 0}

    def predict_with_image(
        self, demographics: Dict[str, Any], image_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Predict biological retinal age + delta vs chronological.

        Returns {biological_age, chronological_age, delta_years,
        accelerated} where `accelerated` is True when delta > +5 years
        (a typical clinical threshold for systemic-aging concern)."""
        base = self.predict_dict(demographics or {})
        if base is None:
            return None
        bio_age = base.get("value")
        if bio_age is None:
            return None

        out: Dict[str, Any] = {"biological_age": float(bio_age)}
        chrono = demographics.get("age") if demographics else None
        if isinstance(chrono, (int, float)) and chrono > 0:
            delta = float(bio_age) - float(chrono)
            out["chronological_age"] = float(chrono)
            out["delta_years"] = round(delta, 1)
            out["accelerated"] = delta > 5.0
            out["label"] = (
                f"Bio age {bio_age:.1f}y vs chrono {chrono:.0f}y (Δ {delta:+.1f}y)"
            )
        else:
            out["label"] = f"Bio age {bio_age:.1f}y (no chronological for delta)"

        if image_path:
            out["image_path"] = image_path
            out["image_used_by_model"] = False
        return out


_singleton: Optional[RetinalAgeAdapter] = None


def get_retinal_age() -> RetinalAgeAdapter:
    """Lazy singleton — load on first access, reuse forever."""
    global _singleton
    if _singleton is None:
        _singleton = RetinalAgeAdapter()
        _singleton.load()
    return _singleton

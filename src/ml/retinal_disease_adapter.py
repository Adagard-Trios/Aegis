"""
Runtime adapter for the retinal_disease pipeline (ODIR-5K metadata).

Today's pipeline trains on metadata features (age, sex, image_path) —
the full EfficientNetV2-M architecture from the source notebook is a
follow-up upgrade. This adapter consumes patient metadata + (when
provided) an uploaded fundus image path; the image_path is recorded in
the prediction output but the underlying classifier currently only uses
the age + sex tabular features. Once the image-aware model lands, swap
in the CNN here without changing the adapter's external contract.

Weight placement:
    models/ocular/retinal_disease/model.pkl  (produced by
    `python models/retinal_disease/export_runtime.py`)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.ml._pickle_adapter import PickledTabularAdapter

logger = logging.getLogger(__name__)


class RetinalDiseaseAdapter(PickledTabularAdapter):
    WEIGHTS_SUBPATH = "ocular/retinal_disease/model.pkl"
    DOMAIN_LABEL = "retinal_disease"
    # ODIR-5K 8-class set: Normal, Diabetes, Glaucoma, Cataract, AMD,
    # Hypertensive, Myopia, Other diseases/abnormalities
    LABELS = ["Normal", "Diabetes", "Glaucoma", "Cataract", "AMD", "Hypertensive", "Myopia", "Other"]

    _FEATURES = ["age", "sex_male"]

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Build {age, sex_male} from patient demographics. `image_path`
        is captured separately on the prediction return path (below)."""
        if not input_dict:
            return {}
        sex = (input_dict.get("sex") or "").strip().lower()
        return {
            "age": input_dict.get("age"),
            "sex_male": 1 if sex.startswith("m") else 0,
        }

    def predict_with_image(
        self, demographics: Dict[str, Any], image_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Public entrypoint — accepts demographics + an optional fundus
        image path. The image_path is included in the response metadata
        so downstream tooling (PDF report builders, audit log) can link
        the prediction back to the source image, even when the current
        tabular model doesn't yet consume it for inference."""
        result = self.predict_dict(demographics or {})
        if result is None:
            return None
        if image_path:
            result["image_path"] = image_path
            result["image_used_by_model"] = False  # honest about current scaffold
        return result


_singleton: Optional[RetinalDiseaseAdapter] = None


def get_retinal_disease() -> RetinalDiseaseAdapter:
    """Lazy singleton — load on first access, reuse forever."""
    global _singleton
    if _singleton is None:
        _singleton = RetinalDiseaseAdapter()
        _singleton.load()
    return _singleton

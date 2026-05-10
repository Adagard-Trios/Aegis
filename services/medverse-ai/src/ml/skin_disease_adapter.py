"""
Runtime adapter for the skin_disease pipeline (HAM10000,
RandomForestClassifier on tabular metadata; 7-class dermatoscopic label).

Same image-aware contract as the retina adapters: `predict_with_image`
accepts a skin lesion image path, the response carries the path through
for the audit / report layer to link back to the source. Today's
underlying classifier uses age + image_path metadata only — once an
image-aware model lands (EfficientNet / ResNet on the lesion crop),
swap in here without changing the adapter's external surface.

Weight placement: models/dermatology/skin_disease/model.pkl
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.ml._pickle_adapter import PickledTabularAdapter

logger = logging.getLogger(__name__)


class SkinDiseaseAdapter(PickledTabularAdapter):
    WEIGHTS_SUBPATH = "dermatology/skin_disease/model.pkl"
    DOMAIN_LABEL = "skin_disease"
    # HAM10000 7-class set (canonical):
    #   akiec = Actinic keratosis / intraepithelial carcinoma
    #   bcc   = Basal cell carcinoma
    #   bkl   = Benign keratosis-like lesion
    #   df    = Dermatofibroma
    #   mel   = Melanoma
    #   nv    = Melanocytic nevus
    #   vasc  = Vascular lesion
    LABELS = ["akiec", "bcc", "bkl", "df", "mel", "nv", "vasc"]

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        if not input_dict:
            return {}
        return {"age": input_dict.get("age")}

    def predict_with_image(
        self, demographics: Dict[str, Any], image_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        result = self.predict_dict(demographics or {})
        if result is None:
            return None
        if image_path:
            result["image_path"] = image_path
            result["image_used_by_model"] = False    # honest about current scaffold
        return result


_singleton: Optional[SkinDiseaseAdapter] = None


def get_skin_disease() -> SkinDiseaseAdapter:
    global _singleton
    if _singleton is None:
        _singleton = SkinDiseaseAdapter()
        _singleton.load()
    return _singleton

"""
Runtime adapter for the bowel_motility pipeline (synthetic 4-channel
gut-sound features, GradientBoostingClassifier; 3-class quiet / normal
/ hyperactive).

Features come from a 4-channel acoustic recording (ch0..ch3 mean / std /
p95). The Aegis vest's I²S mic gives one channel; the AbdomenMonitor
piezo array gives four channels of abdominal acoustics. We map from
those when available; otherwise the trained preprocessor's median
imputer covers the gap.

Consumed by the general_physician graph for GI-state context.

Weight placement: models/general_physician/bowel_motility/model.pkl
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np

from src.ml._pickle_adapter import PickledTabularAdapter

logger = logging.getLogger(__name__)


class BowelMotilityAdapter(PickledTabularAdapter):
    WEIGHTS_SUBPATH = "general_physician/bowel_motility/model.pkl"
    DOMAIN_LABEL = "bowel_motility"
    LABELS = ["quiet", "normal", "hyperactive"]

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Build {ch0_mean, ch0_std, ch0_p95, ch1_*, ch2_*, ch3_*}.

        Sources (in order of preference):
          1. snapshot.fetal.piezo_raw[0..3] from the AbdomenMonitor (4 channels)
          2. snapshot.audio.digital_rms (single channel — fills ch0_* only)
        """
        if not input_dict:
            return {}
        row: Dict[str, Any] = {}
        fetal = input_dict.get("fetal") if isinstance(input_dict.get("fetal"), dict) else {}
        piezo = fetal.get("piezo_raw") if isinstance(fetal.get("piezo_raw"), list) else None

        if piezo and len(piezo) >= 1:
            for i in range(4):
                v = piezo[i] if i < len(piezo) else None
                if v is None:
                    continue
                # Single-sample stand-in — true windowed stats need a buffer
                row[f"ch{i}_mean"] = float(v)
                row[f"ch{i}_std"] = 0.0
                row[f"ch{i}_p95"] = float(v)
        else:
            audio = input_dict.get("audio") if isinstance(input_dict.get("audio"), dict) else {}
            rms = audio.get("digital_rms") or audio.get("analog_rms")
            if rms is not None:
                row["ch0_mean"] = float(rms)
                row["ch0_std"] = 0.0
                row["ch0_p95"] = float(rms)
        return row


_singleton: Optional[BowelMotilityAdapter] = None


def get_bowel_motility() -> BowelMotilityAdapter:
    global _singleton
    if _singleton is None:
        _singleton = BowelMotilityAdapter()
        _singleton.load()
    return _singleton

"""
Runtime adapter for the parkinson_screener pipeline (UCI Parkinsons voice
features, RandomForestClassifier; binary status 0/1).

Voice features (MDVP:Fo, jitter, shimmer, NHR, HNR, RPDE, DFA, spread1,
spread2, D2, PPE) come from a separate voice recording — they're not in
the live vitals snapshot. The runtime usage is `predict_with_features
(feature_dict)` from a voice-analysis upload (deferred — for now the
adapter returns None when no voice features are supplied).

The neurology graph also gets passive IMU-tremor signal as supporting
evidence even when no voice recording is present. The vest's existing
IMU-derived tremor flag (snapshot.imu_derived.tremor.tremor_flag) is
the trigger to surface the screener output.

Weight placement: models/neurology/parkinson_screener/model.pkl
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.ml._pickle_adapter import PickledTabularAdapter

logger = logging.getLogger(__name__)


class ParkinsonScreenerAdapter(PickledTabularAdapter):
    WEIGHTS_SUBPATH = "neurology/parkinson_screener/model.pkl"
    DOMAIN_LABEL = "parkinson_screener"
    LABELS = ["healthy", "parkinson"]

    # UCI Parkinsons voice feature schema
    _FEATURES = [
        "MDVP:Fo(Hz)", "MDVP:Fhi(Hz)", "MDVP:Flo(Hz)",
        "MDVP:Jitter(%)", "MDVP:Jitter(Abs)", "MDVP:RAP",
        "MDVP:PPQ", "Jitter:DDP",
        "MDVP:Shimmer", "MDVP:Shimmer(dB)", "Shimmer:APQ3",
        "Shimmer:APQ5", "MDVP:APQ", "Shimmer:DDA",
        "NHR", "HNR", "RPDE", "DFA", "spread1", "spread2",
        "D2", "PPE",
    ]

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Voice features arrive as a flat dict from a voice-analysis
        upload. Returns empty when no voice data was supplied — the
        graph then skips this adapter rather than imputing junk into
        clinically-meaningful UCI feature columns."""
        if not input_dict:
            return {}
        voice = input_dict.get("voice_features") if isinstance(input_dict.get("voice_features"), dict) else input_dict
        if not any(voice.get(f) is not None for f in self._FEATURES):
            return {}    # signals "skip me" to the base predict_dict
        return {f: voice.get(f) for f in self._FEATURES}


_singleton: Optional[ParkinsonScreenerAdapter] = None


def get_parkinson_screener() -> ParkinsonScreenerAdapter:
    global _singleton
    if _singleton is None:
        _singleton = ParkinsonScreenerAdapter()
        _singleton.load()
    return _singleton

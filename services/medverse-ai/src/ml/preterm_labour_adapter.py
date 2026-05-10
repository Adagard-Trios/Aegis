"""
Runtime adapter for the preterm_labour pipeline (TPEHGDB / TPEHGT EMG).

Consumes uterine activity features from the live fetal monitor + any
contraction-pattern derived metrics, returns a binary risk classification
(Term / Preterm-risk) for the gynecology graph.

Weight placement:
    models/obstetrics/preterm_labour/model.pkl  (produced by
    `python models/preterm_labour/export_runtime.py`)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.ml._pickle_adapter import PickledTabularAdapter

logger = logging.getLogger(__name__)


class PretermLabourAdapter(PickledTabularAdapter):
    WEIGHTS_SUBPATH = "obstetrics/preterm_labour/model.pkl"
    DOMAIN_LABEL = "preterm_labour"
    LABELS = ["Term", "PretermRisk"]

    # Feature set follows the typical EMG-derived feature engineering used
    # for TPEHGDB classification: time-domain (RMS, mean), frequency-domain
    # (spectral median frequency), plus clinical context (gestational age,
    # contraction count). The trained preprocessor's median-imputer
    # backfills any field the live snapshot can't supply.
    _FEATURES = [
        "gestational_age_weeks",
        "rms_emg",
        "mean_emg",
        "median_freq_emg",
        "peak_freq_emg",
        "contractions_per_min",
        "contraction_amplitude_mean",
        "interval_mean_s",
        "interval_cv",
    ]

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Build a feature dict from the snapshot. Accepts both the full
        snapshot (we'll dig out fetal/patient blocks ourselves) and a
        pre-flattened dict from the caller."""
        if not input_dict:
            return {}

        # Allow either {fetal: {...}, patient: {...}} or flat keys
        fetal = input_dict.get("fetal") if isinstance(input_dict.get("fetal"), dict) else input_dict
        patient = input_dict.get("patient") if isinstance(input_dict.get("patient"), dict) else {}

        row: Dict[str, Any] = {}
        for f in self._FEATURES:
            row[f] = (
                input_dict.get(f)
                or (fetal.get(f) if isinstance(fetal, dict) else None)
                or (patient.get(f) if isinstance(patient, dict) else None)
            )
        return row


_singleton: Optional[PretermLabourAdapter] = None


def get_preterm_labour() -> PretermLabourAdapter:
    """Lazy singleton — load on first access, reuse forever."""
    global _singleton
    if _singleton is None:
        _singleton = PretermLabourAdapter()
        _singleton.load()
    return _singleton

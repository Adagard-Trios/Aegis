"""
Runtime adapter for the fetal_health pipeline (UCI CTG, RandomForest baseline).

Consumes the live Dawes-Redman analyser output + raw CTG features from the
gynecology graph's telemetry slice, returns a 3-class classification
(Normal / Suspect / Pathological) suitable for the LLM to ground its
obstetric assessment.

Weight placement:
    models/obstetrics/fetal_health/model.pkl  (produced by
    `python models/fetal_health/export_runtime.py` after training)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.ml._pickle_adapter import PickledTabularAdapter

logger = logging.getLogger(__name__)


class FetalHealthAdapter(PickledTabularAdapter):
    WEIGHTS_SUBPATH = "obstetrics/fetal_health/model.pkl"
    DOMAIN_LABEL = "fetal_health"
    # UCI CTG labels: 1=Normal, 2=Suspect, 3=Pathological
    LABELS = ["Normal", "Suspect", "Pathological"]

    # The 22 features the UCI CTG model expects. Live telemetry doesn't
    # carry all of them — we pass what we have and rely on the trained
    # preprocessor's median-imputer to fill the gaps. The mapping prefers
    # values from the live Dawes-Redman analyser when present; missing
    # features default to None which the imputer handles.
    _FEATURE_MAP = {
        # Acceleration, contraction, movement
        "baseline value": ("dawes_redman", "baseline_fhr"),
        "accelerations": ("dawes_redman", "accelerations_per_min"),
        "fetal_movement": ("fetal", "movement_count"),
        "uterine_contractions": ("fetal", "contractions_per_min"),
        "light_decelerations": ("dawes_redman", "light_decelerations"),
        "severe_decelerations": ("dawes_redman", "severe_decelerations"),
        "prolongued_decelerations": ("dawes_redman", "prolonged_decelerations"),
        "abnormal_short_term_variability": ("dawes_redman", "abnormal_stv_pct"),
        "mean_value_of_short_term_variability": ("dawes_redman", "stv_ms"),
        "percentage_of_time_with_abnormal_long_term_variability": ("dawes_redman", "abnormal_ltv_pct"),
        "mean_value_of_long_term_variability": ("dawes_redman", "ltv_ms"),
        # Histogram features — typically derived from a 30-min CTG window
        "histogram_width": ("dawes_redman", "hist_width"),
        "histogram_min": ("dawes_redman", "hist_min"),
        "histogram_max": ("dawes_redman", "hist_max"),
        "histogram_number_of_peaks": ("dawes_redman", "hist_peaks"),
        "histogram_number_of_zeroes": ("dawes_redman", "hist_zeroes"),
        "histogram_mode": ("dawes_redman", "hist_mode"),
        "histogram_mean": ("dawes_redman", "hist_mean"),
        "histogram_median": ("dawes_redman", "hist_median"),
        "histogram_variance": ("dawes_redman", "hist_variance"),
        "histogram_tendency": ("dawes_redman", "hist_tendency"),
    }

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Build a feature dict from telemetry. `input_dict` is the
        snapshot's `fetal` block — a mix of dawes_redman + raw fetal fields."""
        if not input_dict:
            return {}
        row: Dict[str, Any] = {}
        for col, (group, key) in self._FEATURE_MAP.items():
            sub = input_dict.get(group) if isinstance(input_dict.get(group), dict) else None
            row[col] = sub.get(key) if sub else input_dict.get(key)
        return row


_singleton: Optional[FetalHealthAdapter] = None


def get_fetal_health() -> FetalHealthAdapter:
    """Lazy singleton — load on first access, reuse forever."""
    global _singleton
    if _singleton is None:
        _singleton = FetalHealthAdapter()
        _singleton.load()
    return _singleton

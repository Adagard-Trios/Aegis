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

    # The 34 columns the trained UCI CTG model's preprocessor expects.
    # Names are the UCI dataset's abbreviated codes — the trained
    # Pipeline's median imputer fills any column we leave None, so we
    # only need to supply the ones the live Dawes-Redman analyser
    # actually computes. The morphology pattern flags (A-E, AD, DE, LD,
    # FS) and meta-cols (SUSP, CLASS) get NaN -> median from training.
    _FEATURE_MAP = {
        # Direct live values from Dawes-Redman + raw fetal block
        "LB":   ("dawes_redman", "baseline_fhr"),
        "LBE":  ("dawes_redman", "baseline_fhr"),    # encoded baseline; usually == LB
        "AC":   ("dawes_redman", "accelerations_per_min"),
        "FM":   ("fetal", "movement_count"),
        "UC":   ("fetal", "contractions_per_min"),
        "DL":   ("dawes_redman", "light_decelerations"),
        "DS":   ("dawes_redman", "severe_decelerations"),
        "DP":   ("dawes_redman", "prolonged_decelerations"),
        "DR":   ("dawes_redman", "prolonged_decelerations"),    # rapid; aliased to prolonged
        "ASTV": ("dawes_redman", "abnormal_stv_pct"),
        "MSTV": ("dawes_redman", "stv_ms"),
        "ALTV": ("dawes_redman", "abnormal_ltv_pct"),
        "MLTV": ("dawes_redman", "ltv_ms"),
        "Width":    ("dawes_redman", "hist_width"),
        "Min":      ("dawes_redman", "hist_min"),
        "Max":      ("dawes_redman", "hist_max"),
        "Nmax":     ("dawes_redman", "hist_peaks"),
        "Nzeros":   ("dawes_redman", "hist_zeroes"),
        "Mode":     ("dawes_redman", "hist_mode"),
        "Mean":     ("dawes_redman", "hist_mean"),
        "Median":   ("dawes_redman", "hist_median"),
        "Variance": ("dawes_redman", "hist_variance"),
        "Tendency": ("dawes_redman", "hist_tendency"),
        # Pattern morphology flags + class labels — the live analyser
        # doesn't compute these. Mapped to None so the trained imputer
        # fills them with the training median (acts as a "no opinion"
        # marker for these auxiliary features).
        "A":  (None, None), "B":  (None, None), "C":  (None, None),
        "D":  (None, None), "E":  (None, None), "AD": (None, None),
        "DE": (None, None), "LD": (None, None), "FS": (None, None),
        "SUSP":  (None, None), "CLASS": (None, None),
    }

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Build a feature dict matching the trained UCI CTG column set.
        `input_dict` is the snapshot's `fetal` block — a mix of
        `dawes_redman` + raw fetal fields. Columns we can't derive
        live (pattern flags, meta-cols) are passed as None so the
        trained median-imputer covers them."""
        if not input_dict:
            return {}
        row: Dict[str, Any] = {}
        for col, (group, key) in self._FEATURE_MAP.items():
            if group is None:
                row[col] = None
                continue
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

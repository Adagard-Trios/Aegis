"""
Runtime adapter for the lung_sound pipeline (ICBHI 2017,
RandomForestClassifier on simple time-domain audio features).

Distinct from src/ml/pulmonary_classifier.py — that adapter is the
ICBHI-CNN respiratory event classifier (wheeze / crackle / etc), this
one is the patient-level diagnostic classifier (Healthy / COPD / Asthma
/ Pneumonia / Bronchiectasis / Bronchiolitis / URTI / LRTI).

Both can run side-by-side on the pulmonary graph — the LLM gets two
independent perspectives.

Weight placement: models/pulmonary/lung_sound/model.pkl
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np

from src.ml._pickle_adapter import PickledTabularAdapter

logger = logging.getLogger(__name__)


class LungSoundAdapter(PickledTabularAdapter):
    WEIGHTS_SUBPATH = "pulmonary/lung_sound/model.pkl"
    DOMAIN_LABEL = "lung_sound"
    # Set at load time from class_names.json sibling, fallback to ICBHI defaults
    LABELS = [
        "Healthy", "COPD", "Asthma", "Pneumonia",
        "Bronchiectasis", "Bronchiolitis", "URTI", "LRTI",
    ]

    def _to_feature_row(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Build features from the vitals snapshot's audio block + waveform.

        The pipeline trained on (duration_s, rms, zcr, p95, p05). The live
        snapshot exposes audio.digital_rms; if waveform.audio is present
        we derive zcr / p95 / p05 from it. Anything missing is imputed by
        the trained preprocessor.
        """
        if not input_dict:
            return {}
        audio = input_dict.get("audio") if isinstance(input_dict.get("audio"), dict) else {}
        waveform = (input_dict.get("waveform") or {}) if isinstance(input_dict.get("waveform"), dict) else {}

        row = {
            "duration_s": None,
            "rms": audio.get("digital_rms") or audio.get("analog_rms"),
            "zcr": None,
            "p95": None,
            "p05": None,
        }

        wav_audio = waveform.get("audio") if isinstance(waveform, dict) else None
        if wav_audio:
            try:
                a = np.asarray(wav_audio, dtype=float)
                if a.size:
                    fs = waveform.get("fs") or 40
                    row["duration_s"] = float(a.size / max(fs, 1))
                    if row["rms"] is None:
                        row["rms"] = float(np.sqrt(np.mean(a * a)))
                    # Zero-crossing rate
                    zc = np.sum(np.diff(np.sign(a)) != 0)
                    row["zcr"] = float(zc / max(a.size, 1))
                    row["p95"] = float(np.percentile(np.abs(a), 95))
                    row["p05"] = float(np.percentile(np.abs(a), 5))
            except Exception:
                pass
        return row


_singleton: Optional[LungSoundAdapter] = None


def get_lung_sound() -> LungSoundAdapter:
    global _singleton
    if _singleton is None:
        _singleton = LungSoundAdapter()
        _singleton.load()
    return _singleton

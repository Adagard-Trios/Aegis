"""LangGraph-compatible tools that invoke the trained models in models/<slug>/.

The factory builds @tool functions that:
  1. Resolve the latest trained-model artifact for a pipeline slug via
     models.registry.trained_model_path().
  2. Load the pickled ModelEstimator (preprocessor + model bundle).
  3. Run prediction over the latest telemetry snapshot (pulled from SQLite
     or built on the fly), and return a JSON string the agent can read.

When a pipeline hasn't been trained yet, the tool returns a structured
"model_unavailable" payload instead of raising — so the graphs degrade
gracefully and the user gets a useful message in the chat.
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Add the repo root to sys.path so models.* imports resolve when the agent
# runner runs from a different cwd.
import os
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _latest_snapshot() -> Dict[str, Any]:
    """Pull the latest telemetry snapshot. Falls back to {} on failure."""
    try:
        from src.utils.db import get_latest_telemetry, DEFAULT_PATIENT_ID
        return get_latest_telemetry(patient_id=DEFAULT_PATIENT_ID) or {}
    except Exception as e:
        logger.debug(f"_latest_snapshot fallback: {e}")
        return {}


def _load_estimator(slug: str):
    """Load the ModelEstimator pickle for `slug`. Returns None when no model."""
    try:
        from models.registry import trained_model_path
        path = trained_model_path(slug)
    except Exception as e:
        logger.error(f"registry lookup failed for {slug}: {e}")
        return None
    if not path:
        return None
    try:
        import pickle
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        logger.error(f"failed to load {slug} model from {path}: {e}")
        return None


def _features_for(slug: str, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Per-pipeline feature extraction from the live telemetry snapshot.

    Each branch projects the snapshot down to the columns the model was
    trained on. Override / extend per pipeline as the schema evolves.
    """
    v = snapshot.get("vitals") or {}
    e = snapshot.get("ecg") or {}
    imu = snapshot.get("imu") or {}
    der = snapshot.get("imu_derived") or {}
    fetal = snapshot.get("fetal") or {}
    audio = snapshot.get("audio") or {}
    temp = snapshot.get("temperature") or {}

    if slug == "ecg_arrhythmia":
        return {
            "heart_rate": v.get("heart_rate"),
            "hrv_rmssd": v.get("hrv_rmssd"),
            "ecg_hr": e.get("ecg_hr"),
            "lead1": e.get("lead1"),
            "lead2": e.get("lead2"),
            "lead3": e.get("lead3"),
        }
    if slug == "cardiac_age":
        return {
            "heart_rate": v.get("heart_rate"),
            "hrv_rmssd": v.get("hrv_rmssd"),
            "ecg_hr": e.get("ecg_hr"),
        }
    if slug == "ecg_biometric":
        return {
            "lead1": e.get("lead1"),
            "lead2": e.get("lead2"),
            "lead3": e.get("lead3"),
        }
    if slug == "lung_sound":
        return {
            "spo2": v.get("spo2"),
            "breathing_rate": v.get("breathing_rate"),
            "audio_analog": audio.get("analog_rms"),
            "audio_digital": audio.get("digital_rms"),
        }
    if slug == "parkinson_screener":
        tremor = der.get("tremor") or {}
        gait = der.get("gait") or {}
        return {
            "tremor_band_power": tremor.get("band_power"),
            "tremor_band_ratio": tremor.get("band_ratio"),
            "gait_stride_cv": gait.get("stride_cv"),
            "gait_asymmetry_flag": gait.get("asymmetry_flag"),
            "spinal_angle": imu.get("spinal_angle"),
            "activity_state": der.get("activity_state"),
        }
    if slug == "fetal_health":
        dr = fetal.get("dawes_redman") or {}
        return {
            "fhr_baseline": dr.get("fhr_baseline"),
            "stv": dr.get("short_term_variability"),
            "ltv": dr.get("long_term_variability"),
            "decelerations": dr.get("decelerations"),
            "reactivity": dr.get("reactivity"),
            "kicks": sum(1 for k in (fetal.get("kicks") or []) if k),
            "contractions": sum(1 for c in (fetal.get("contractions") or []) if c),
        }
    if slug == "preterm_labour":
        return {
            "contractions": sum(1 for c in (fetal.get("contractions") or []) if c),
            "kicks": sum(1 for k in (fetal.get("kicks") or []) if k),
            "maternal_hr": v.get("heart_rate"),
            "maternal_temp": temp.get("cervical"),
        }
    if slug == "skin_disease":
        return {
            "left_axilla_temp": temp.get("left_axilla"),
            "right_axilla_temp": temp.get("right_axilla"),
            "cervical_temp": temp.get("cervical"),
        }
    if slug in ("retinal_disease", "retinal_age"):
        # Image-based — vest doesn't carry a retinal camera; the tool returns
        # "image_required" so the agent knows it can't be inferred from telemetry.
        return None
    return None


def _build_unavailable_payload(slug: str, reason: str) -> str:
    return json.dumps({
        "model": slug,
        "status": "model_unavailable",
        "reason": reason,
        "hint": f"Train this pipeline first: cd models/{slug} && python main.py",
    })


def make_model_tool(slug: str, name: str, description: str):
    """Factory: build a LangChain @tool that runs the trained pipeline `slug`."""

    @tool(name, description=description, parse_docstring=False)
    def _tool() -> str:  # noqa: D401 — short tool docstring set via decorator
        try:
            estimator = _load_estimator(slug)
            if estimator is None:
                return _build_unavailable_payload(slug, "no trained-model artifact found")

            snapshot = _latest_snapshot()
            features = _features_for(slug, snapshot)
            if features is None:
                return _build_unavailable_payload(slug, "input modality (e.g. retinal image) not in vest telemetry")
            # Drop None values; the preprocessor expects numeric / present cols.
            features = {k: v for k, v in features.items() if v is not None}
            if not features:
                return _build_unavailable_payload(slug, "no usable features in current snapshot")

            try:
                import pandas as pd
                df = pd.DataFrame([features])
                preds = estimator.predict(df)
                proba = None
                try:
                    p = estimator.predict_proba(df)
                    proba = p[0].tolist() if hasattr(p, "__getitem__") else None
                except Exception:
                    pass
                return json.dumps({
                    "model": slug,
                    "status": "ok",
                    "prediction": preds[0] if hasattr(preds, "__getitem__") and len(preds) else preds,
                    "probabilities": proba,
                    "features_used": list(features.keys()),
                })
            except Exception as e:
                return json.dumps({
                    "model": slug,
                    "status": "prediction_error",
                    "error": str(e),
                })
        except Exception as e:
            return json.dumps({"model": slug, "status": "error", "error": str(e)})

    return _tool


# ─── Built-in tools per pipeline ────────────────────────────────────────────
# Each gets a stable name agents can reference in their reasoning.

predict_ecg_arrhythmia = make_model_tool(
    "ecg_arrhythmia",
    "predict_ecg_arrhythmia",
    "Run the ECG arrhythmia classifier on the latest ECG snapshot. Returns "
    "{prediction, probabilities, status}. Use when investigating rhythm "
    "abnormalities, ST changes, or PVCs.",
)

predict_cardiac_age = make_model_tool(
    "cardiac_age",
    "predict_cardiac_age",
    "Estimate cardiovascular biological age from HR, HRV and ECG-derived "
    "features. Returns a regression value in years. Use to flag accelerated "
    "vascular ageing.",
)

predict_ecg_biometric = make_model_tool(
    "ecg_biometric",
    "predict_ecg_biometric",
    "Run the ECG-biometric Siamese identity check on the latest ECG snapshot. "
    "Returns the matched-identity confidence. Use to verify the wearer.",
)

predict_lung_sound = make_model_tool(
    "lung_sound",
    "predict_lung_sound",
    "Classify lung-sound recording: normal / wheeze / crackle / rhonchi from "
    "the I²S acoustic stream and respiratory vitals.",
)

predict_parkinson = make_model_tool(
    "parkinson_screener",
    "predict_parkinson",
    "Run Parkinson screening on IMU-derived tremor band-power, gait CV, and "
    "posture. Returns a probability + risk band.",
)

predict_fetal_health = make_model_tool(
    "fetal_health",
    "predict_fetal_health",
    "Classify fetal CTG status (Normal / Suspect / Pathological) from "
    "Dawes-Redman fields, kicks, and contractions.",
)

predict_preterm_labour = make_model_tool(
    "preterm_labour",
    "predict_preterm_labour",
    "Estimate the probability of preterm labour from contraction frequency, "
    "kicks, and maternal vitals.",
)

predict_skin_disease = make_model_tool(
    "skin_disease",
    "predict_skin_disease",
    "Skin-condition classifier based on multi-site temperature gradients. "
    "Image-based extension requires uploading via /api/upload-lab-results.",
)

predict_retinal_disease = make_model_tool(
    "retinal_disease",
    "predict_retinal_disease",
    "Retinal disease classifier — REQUIRES a retinal image. The vest does "
    "not capture this; returns 'image_required' until a retinal-image "
    "endpoint is wired.",
)

predict_retinal_age = make_model_tool(
    "retinal_age",
    "predict_retinal_age",
    "Retinal biological-age regression — image-required (see retinal_disease).",
)


# ─── Specialty → model-tool mapping ─────────────────────────────────────────

SPECIALTY_MODEL_TOOLS: Dict[str, List[Any]] = {
    "Cardiology Expert": [
        predict_ecg_arrhythmia,
        predict_cardiac_age,
        predict_ecg_biometric,
    ],
    "Pulmonology Expert": [
        predict_lung_sound,
    ],
    "Neurology Expert": [
        predict_parkinson,
    ],
    "Dermatology Expert": [
        predict_skin_disease,
    ],
    "Obstetrics Expert": [
        predict_fetal_health,
        predict_preterm_labour,
    ],
    "Ocular Expert": [
        predict_retinal_disease,
        predict_retinal_age,
    ],
    "General Physician": [],  # synthesises specialty outputs; no direct ML
}


def get_model_tools(specialty: str) -> List[Any]:
    """Return the list of model-prediction tools registered for a specialty."""
    return SPECIALTY_MODEL_TOOLS.get(specialty, [])

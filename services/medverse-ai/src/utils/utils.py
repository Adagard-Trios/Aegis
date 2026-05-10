"""
src/utils/utils.py

Mock sensor-retrieval tools for each specialist subgraph.
Each tool simulates a database/sensor query and returns structured mock data.
In production, these would pull from real-time telemetry or patient databases.
"""
from datetime import datetime

from langchain_core.tools import tool


def get_today_str() -> str:
    return datetime.now().strftime("%a %b %d, %Y %H:%M")


# =============================================================================
# CARDIOLOGY TOOLS
# =============================================================================

@tool
def retrieve_ecg_data() -> str:
    """Retrieve ECG waveform analysis from the vest's AD8232 sensor array."""
    return (
        '{"lead_I": {"rhythm": "normal_sinus", "rate_bpm": 78, "pr_interval_ms": 162, '
        '"qrs_duration_ms": 88, "st_segment": "isoelectric"}, '
        '"lead_II": {"rhythm": "normal_sinus", "rate_bpm": 78, "p_wave": "upright", '
        '"t_wave": "upright", "st_deviation_mm": 0.2}, '
        '"lead_III": {"rhythm": "normal_sinus", "axis_degrees": 55}, '
        '"arrhythmia_flags": [], "recording_duration_s": 30}'
    )


@tool
def retrieve_cardiac_biomarkers() -> str:
    """Retrieve cardiac biomarker levels from the patient database."""
    return (
        '{"troponin_i_ng_ml": 0.012, "bnp_pg_ml": 45, "nt_probnp_pg_ml": 120, '
        '"ck_mb_ng_ml": 2.1, "d_dimer_ng_ml": 180, "timestamp": "2024-03-23T14:30:00"}'
    )


@tool
def retrieve_blood_pressure() -> str:
    """Retrieve blood pressure and hemodynamic data from cuff/PPG sensor."""
    return (
        '{"systolic_mmhg": 122, "diastolic_mmhg": 78, "map_mmhg": 93, '
        '"pulse_pressure_mmhg": 44, "heart_rate_bpm": 78, '
        '"hrv_sdnn_ms": 112, "hrv_rmssd_ms": 38, "lf_hf_ratio": 1.4}'
    )


# =============================================================================
# PULMONOLOGY TOOLS
# =============================================================================

@tool
def retrieve_respiratory_data() -> str:
    """Retrieve respiratory telemetry from the I2S acoustic array and pneumogram."""
    return (
        '{"respiratory_rate": 16, "tidal_volume_ml": 520, "minute_ventilation_l": 8.3, '
        '"inspiratory_time_s": 1.8, "expiratory_time_s": 2.4, "ie_ratio": "1:1.3", '
        '"breath_sounds": "clear_bilateral", "adventitious_sounds": []}'
    )


@tool
def retrieve_spo2_data() -> str:
    """Retrieve pulse oximetry and blood gas data from MAX30102 PPG sensor."""
    return (
        '{"spo2_percent": 98, "perfusion_index": 3.2, "pleth_variability_index": 12, '
        '"signal_quality": "good", "probe_site": "finger", '
        '"etco2_mmhg": 38, "fio2": 0.21}'
    )


# =============================================================================
# NEUROLOGY / BIOMECHANICS TOOLS
# =============================================================================

@tool
def retrieve_imu_posture_data() -> str:
    """Retrieve IMU accelerometer/gyroscope data from MPU6050 on the vest."""
    return (
        '{"posture": "upright", "spinal_angle_degrees": 3.2, '
        '"sagittal_balance_cm": 1.1, "lateral_tilt_degrees": 0.8, '
        '"accelerometer_g": {"x": 0.02, "y": 0.98, "z": 0.05}, '
        '"gyroscope_dps": {"x": 1.2, "y": 0.3, "z": 0.8}}'
    )


@tool
def retrieve_fall_detection_data() -> str:
    """Retrieve fall detection and motion analysis from the IMU sensor."""
    return (
        '{"fall_detected": false, "last_fall_event": null, '
        '"gait_stability_score": 0.92, "step_count_last_hour": 340, '
        '"tremor_detected": false, "tremor_frequency_hz": null, '
        '"balance_score": 0.88, "morse_fall_risk_score": 15}'
    )


@tool
def retrieve_sleep_data() -> str:
    """Retrieve sleep staging data from combined EEG/IMU/HRV analysis."""
    return (
        '{"sleep_stage": "awake", "total_sleep_time_min": null, '
        '"sleep_efficiency_percent": null, "rem_latency_min": null, '
        '"movement_index": 0.12, "hrv_during_sleep": null}'
    )


# =============================================================================
# DERMATOLOGY TOOLS
# =============================================================================

@tool
def retrieve_skin_temperature_map() -> str:
    """Retrieve DS18B20 temperature array data from 3 vest zones."""
    return (
        '{"left_axilla_c": 36.5, "right_axilla_c": 36.6, "cervical_c7_c": 36.8, '
        '"bilateral_difference_c": 0.1, "ambient_temp_c": 24.5, '
        '"core_skin_gradient_c": 2.8, "diaphoresis_detected": false}'
    )


@tool
def retrieve_dermal_assessment() -> str:
    """Retrieve dermatological assessment indicators from skin sensors."""
    return (
        '{"skin_moisture": "normal", "skin_color_change": false, '
        '"localized_hot_spots": [], "localized_cold_spots": [], '
        '"rash_detected": false, "thermal_anomaly_zones": []}'
    )


# =============================================================================
# OBSTETRICS / GYNECOLOGY TOOLS
# =============================================================================

@tool
def retrieve_foetal_heart_rate() -> str:
    """Retrieve foetal heart rate and CTG data from obstetric sensors."""
    return (
        '{"fhr_baseline_bpm": 142, "fhr_variability_bpm": 12, '
        '"accelerations_count_20min": 3, "decelerations": [], '
        '"ctg_classification": "normal", "reactivity": "reactive", '
        '"sinusoidal_pattern": false}'
    )


@tool
def retrieve_uterine_activity() -> str:
    """Retrieve uterine contraction monitoring data."""
    return (
        '{"contractions_per_10min": 0, "tachysystole": false, '
        '"resting_tone": "normal", "contraction_duration_s": null, '
        '"contraction_intensity": null}'
    )


@tool
def retrieve_maternal_vitals() -> str:
    """Retrieve maternal vital signs relevant to obstetric monitoring."""
    return (
        '{"maternal_hr_bpm": 76, "maternal_bp_systolic": 118, '
        '"maternal_bp_diastolic": 72, "maternal_temp_c": 36.7, '
        '"maternal_spo2": 99, "foetal_kick_count_2hr": 14}'
    )


# =============================================================================
# OCULAR TOOLS
# =============================================================================

@tool
def retrieve_pupil_assessment() -> str:
    """Retrieve pupillary response data from ocular sensors."""
    return (
        '{"left_pupil_mm": 3.5, "right_pupil_mm": 3.4, '
        '"anisocoria_mm": 0.1, "light_reflex_left": "brisk", '
        '"light_reflex_right": "brisk", "consensual_reflex": "intact", '
        '"rapd_detected": false, "accommodation": "normal"}'
    )


@tool
def retrieve_iop_data() -> str:
    """Retrieve intraocular pressure measurements."""
    return (
        '{"left_iop_mmhg": 15, "right_iop_mmhg": 14, '
        '"measurement_method": "estimated_ppg", '
        '"iop_trend": "stable", "at_risk_glaucoma": false}'
    )


# =============================================================================
# GENERAL PHYSICIAN TOOLS
# =============================================================================

@tool
def retrieve_vitals_summary() -> str:
    """Retrieve comprehensive vital sign summary from all vest sensors."""
    return (
        '{"heart_rate_bpm": 78, "respiratory_rate": 16, "spo2_percent": 98, '
        '"systolic_bp": 122, "diastolic_bp": 78, "temperature_c": 36.8, '
        '"map_mmhg": 93, "gcs_score": 15, "pain_score": 0, '
        '"mews_score": 1, "avpu": "alert"}'
    )


@tool
def retrieve_patient_history() -> str:
    """Retrieve patient medical history and current medications from EHR."""
    return (
        '{"age": 34, "sex": "female", "bmi": 24.2, '
        '"chronic_conditions": [], "current_medications": [], '
        '"allergies": ["penicillin"], "surgical_history": [], '
        '"family_history": ["hypertension_father"], '
        '"last_visit": "2024-02-15"}'
    )


@tool
def retrieve_cross_specialty_flags() -> str:
    """Retrieve cross-specialty alert flags from all active expert agents."""
    return (
        '{"cardiology_flag": "clear", "pulmonary_flag": "clear", '
        '"neurology_flag": "clear", "dermatology_flag": "clear", '
        '"obstetrics_flag": "clear", "ocular_flag": "clear", '
        '"sepsis_screening": "negative", "qsofa_score": 0}'
    )


# =============================================================================
# EXPERT TOOLS REGISTRY — maps specialty → tool list
# =============================================================================

_BASE_EXPERT_TOOLS = {
    "Cardiology Expert": [
        retrieve_ecg_data,
        retrieve_cardiac_biomarkers,
        retrieve_blood_pressure,
    ],
    "Pulmonology Expert": [
        retrieve_respiratory_data,
        retrieve_spo2_data,
    ],
    "Neurology Expert": [
        retrieve_imu_posture_data,
        retrieve_fall_detection_data,
        retrieve_sleep_data,
    ],
    "Dermatology Expert": [
        retrieve_skin_temperature_map,
        retrieve_dermal_assessment,
    ],
    "Obstetrics Expert": [
        retrieve_foetal_heart_rate,
        retrieve_uterine_activity,
        retrieve_maternal_vitals,
    ],
    "Ocular Expert": [
        retrieve_pupil_assessment,
        retrieve_iop_data,
    ],
    "General Physician": [
        retrieve_vitals_summary,
        retrieve_patient_history,
        retrieve_cross_specialty_flags,
    ],
}


def _build_expert_tools():
    """Compose telemetry-retrieval tools with the model-prediction tools
    registered in src.utils.model_tools.SPECIALTY_MODEL_TOOLS."""
    try:
        from src.utils.model_tools import get_model_tools
    except Exception:
        get_model_tools = lambda _s: []  # noqa: E731 — graceful degrade

    composed = {}
    for specialty, tools in _BASE_EXPERT_TOOLS.items():
        composed[specialty] = list(tools) + list(get_model_tools(specialty))
    return composed


EXPERT_TOOLS = _build_expert_tools()

"""
src/utils/imu_features.py

Clinical biomarkers derived from the existing MPU6050 IMU stream.
All helpers operate on rolling buffers that are already maintained in
app.py — no new sensors or sampling-rate changes required.

Four outputs:
  • tremor_fft            — FFT-band power of the 4–8 Hz band (Parkinson's resting tremor)
  • gait_symmetry         — CV of step intervals from the lower IMU (fall-risk surrogate)
  • pots_flag             — postural orthostatic tachycardia: HR jump > 30 bpm on posture change
  • activity_state        — {rest | walking | running} from IMU magnitude variance

All functions are tolerant of short buffers and silent on failure —
they return sensible defaults rather than raising, so the live SSE loop
at 10 Hz never breaks because of a DSP edge case.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Iterable, Literal

import numpy as np
from scipy.signal import welch

ActivityState = Literal["rest", "walking", "running", "unknown"]

# Sample rate matches the vest's BLE stream (see app.py SAMPLE_RATE).
_FS_DEFAULT = 40


def _as_array(buf: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(buf), dtype=float)
    return arr[np.isfinite(arr)]


# ─── Tremor detection ────────────────────────────────────────────────────────

def tremor_fft(
    imu_buf: Iterable[float],
    fs: int = _FS_DEFAULT,
    band: tuple[float, float] = (4.0, 8.0),
) -> dict:
    """
    FFT-band power in the Parkinson's resting-tremor band (default 4–8 Hz).

    Returns:
        {
            "band_power":    <float, mean PSD across the band>,
            "total_power":   <float, mean PSD across 0..fs/2>,
            "band_ratio":    <float, band_power / total_power>,
            "tremor_flag":   <bool, band_ratio > 0.25 AND band_power > 0.01>,
        }
    """
    x = _as_array(imu_buf)
    if len(x) < fs * 4:
        return {"band_power": 0.0, "total_power": 0.0, "band_ratio": 0.0, "tremor_flag": False}

    # De-trend
    x = x - np.mean(x)
    try:
        freqs, psd = welch(x, fs=fs, nperseg=min(256, len(x)))
    except Exception:
        return {"band_power": 0.0, "total_power": 0.0, "band_ratio": 0.0, "tremor_flag": False}

    band_mask = (freqs >= band[0]) & (freqs <= band[1])
    # Use integrated PSD (sum) so band_ratio is a true energy fraction in [0, 1].
    band_power = float(np.sum(psd[band_mask])) if band_mask.any() else 0.0
    total_power = float(np.sum(psd)) if len(psd) else 0.0
    band_ratio = band_power / total_power if total_power > 0 else 0.0
    return {
        "band_power": round(band_power, 4),
        "total_power": round(total_power, 4),
        "band_ratio": round(band_ratio, 4),
        "tremor_flag": bool(band_ratio > 0.25 and band_power > 0.01),
    }


# ─── Gait symmetry ───────────────────────────────────────────────────────────

def gait_symmetry(
    lower_pitch_buf: Iterable[float],
    fs: int = _FS_DEFAULT,
    min_stride_hz: float = 0.5,
    max_stride_hz: float = 3.0,
) -> dict:
    """
    Step-interval coefficient of variation from the lower IMU pitch signal.

    A CV > 10 % is a validated fall-risk marker in gait-lab literature.

    Returns:
        {
            "stride_count":       <int>,
            "mean_stride_s":      <float>,
            "stride_cv":          <float, coefficient of variation>,
            "asymmetry_flag":     <bool, stride_cv > 0.10>,
        }
    """
    from scipy.signal import find_peaks

    x = _as_array(lower_pitch_buf)
    if len(x) < fs * 6:
        return {"stride_count": 0, "mean_stride_s": 0.0, "stride_cv": 0.0, "asymmetry_flag": False}

    x = x - np.mean(x)
    min_dist = int(fs / max_stride_hz)
    try:
        peaks, _ = find_peaks(x, distance=min_dist, prominence=np.std(x) * 0.4)
    except Exception:
        peaks = np.array([])

    if len(peaks) < 3:
        return {"stride_count": int(len(peaks)), "mean_stride_s": 0.0, "stride_cv": 0.0, "asymmetry_flag": False}

    intervals = np.diff(peaks) / fs
    valid = intervals[(intervals >= 1.0 / max_stride_hz) & (intervals <= 1.0 / min_stride_hz)]
    if len(valid) < 2:
        return {"stride_count": int(len(peaks)), "mean_stride_s": 0.0, "stride_cv": 0.0, "asymmetry_flag": False}

    mean_stride = float(np.mean(valid))
    cv = float(np.std(valid) / mean_stride) if mean_stride > 0 else 0.0
    return {
        "stride_count": int(len(peaks)),
        "mean_stride_s": round(mean_stride, 3),
        "stride_cv": round(cv, 4),
        "asymmetry_flag": bool(cv > 0.10),
    }


# ─── POTS detection ──────────────────────────────────────────────────────────

def pots_flag(
    hr_buf: Iterable[float],
    spinal_angle_buf: Iterable[float],
    fs: int = _FS_DEFAULT,
    hr_jump_bpm: float = 30.0,
    angle_delta_deg: float = 20.0,
) -> dict:
    """
    Postural orthostatic tachycardia: heart-rate jump > 30 bpm within 30 s
    of a posture change (spinal-angle delta > 20°).

    Returns:
        {
            "hr_jump":       <float, latest HR - baseline HR>,
            "angle_delta":   <float, latest SA - baseline SA>,
            "pots_flag":     <bool>,
        }
    """
    hr = _as_array(hr_buf)
    sa = _as_array(spinal_angle_buf)
    window = fs * 30
    if len(hr) < window or len(sa) < window:
        return {"hr_jump": 0.0, "angle_delta": 0.0, "pots_flag": False}

    hr_baseline = float(np.mean(hr[-window:-window // 2]))
    hr_latest = float(np.mean(hr[-window // 4:]))
    sa_baseline = float(np.mean(sa[-window:-window // 2]))
    sa_latest = float(np.mean(sa[-window // 4:]))

    hr_jump = hr_latest - hr_baseline
    angle_delta = sa_latest - sa_baseline
    flag = hr_jump > hr_jump_bpm and abs(angle_delta) > angle_delta_deg
    return {
        "hr_jump": round(hr_jump, 2),
        "angle_delta": round(angle_delta, 2),
        "pots_flag": bool(flag),
    }


# ─── Activity state ──────────────────────────────────────────────────────────

def activity_state(
    upper_pitch_buf: Iterable[float],
    lower_pitch_buf: Iterable[float],
    fs: int = _FS_DEFAULT,
) -> ActivityState:
    """
    Coarse activity classification from IMU magnitude variance:
      • var < 1.0     → 'rest'
      • var < 20.0    → 'walking'
      • else          → 'running'
    Used to contextually normalize vitals (a HR of 105 means different
    things at rest vs. running).
    """
    up = _as_array(upper_pitch_buf)
    lp = _as_array(lower_pitch_buf)
    if len(up) < fs or len(lp) < fs:
        return "unknown"
    window = fs * 4
    combined = np.concatenate([up[-window:], lp[-window:]])
    var = float(np.var(combined))
    if var < 1.0:
        return "rest"
    if var < 20.0:
        return "walking"
    return "running"


# ─── Bundle builder ──────────────────────────────────────────────────────────

def build_imu_derived_block(
    up_buf: Iterable[float],
    ur_buf: Iterable[float],
    lp_buf: Iterable[float],
    lr_buf: Iterable[float],
    sa_buf: Iterable[float],
    hr_buf: Iterable[float],
    fs: int = _FS_DEFAULT,
) -> dict:
    """
    Compose the full `imu_derived` block that gets attached to the
    telemetry snapshot. Safe on short / empty buffers.
    """
    # Use the most active axis (upper pitch) for tremor — rest tremor
    # shows up strongest on the distal axis.
    tremor = tremor_fft(list(up_buf) + list(ur_buf), fs=fs)
    gait = gait_symmetry(lp_buf, fs=fs)
    pots = pots_flag(hr_buf, sa_buf, fs=fs)
    state = activity_state(up_buf, lp_buf, fs=fs)
    return {
        "tremor": tremor,
        "gait": gait,
        "pots": pots,
        "activity_state": state,
    }

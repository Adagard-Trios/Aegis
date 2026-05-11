"""
Stateless CTG (cardiotocography) analyzer for the AI service.

Distinct from the stateful src/utils/ctg_dawes_redman.py on the Render
backend, which keeps a 30-min FHR ring buffer per patient. This module
takes a raw FHR sample array straight from the snapshot
(`snapshot["fhr_raw"]`) and produces the dict shape the fetal_health
adapter's `_FEATURE_MAP` expects.

Why a separate module: HF Spaces is stateless across requests (no
guarantee a follow-up request lands on the same warm worker), so we
can't keep a per-patient ring buffer. Mobile / abdomen monitor sends
the most recent FHR window with each agent request, and we extract
the criteria from that window in one call.

Scope note: same simplification as the Render-side analyzer — captures
baseline FHR, STV, accelerations, decelerations + a histogram block.
NOT a clinical-grade Dawes-Redman implementation (that's commercial,
closed-source). Fields the simple analyzer can't compute (light vs
severe vs prolonged decel breakdown, abnormal_stv_pct, ltv) are left
as `None` so the trained UCI CTG preprocessor's median-imputer fills
them at predict time.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


# Decel/accel detection thresholds — match the stateful analyzer.
_EXCURSION_BPM_DELTA = 15.0       # ≥15 bpm change from baseline
_EXCURSION_MIN_SAMPLES = 15       # held ≥15 s at 1 Hz sampling


def _trimmed_baseline(samples: Sequence[float]) -> float:
    """Trimmed mean (drop top/bottom 10%) — robust to brief excursions."""
    if not samples:
        return 0.0
    s = sorted(s for s in samples if s and s > 0)
    if not s:
        return 0.0
    trim = max(1, len(s) // 10)
    if len(s) <= 2 * trim:
        return sum(s) / len(s)
    return sum(s[trim:-trim]) / (len(s) - 2 * trim)


def _stv(samples: Sequence[float]) -> float:
    """Short-term variation (mean abs Δ between consecutive RRs, in ms).
    Approximation: |Δ FHR| × 60_000 / (FHR² × 1) — small-angle approx
    to Δ RR-interval. Matches the simplification used by the stateful
    analyzer."""
    if len(samples) < 2:
        return 0.0
    deltas = []
    for a, b in zip(samples[:-1], samples[1:]):
        if a > 0 and b > 0:
            mean_fhr = (a + b) / 2.0
            d_rr_ms = abs(60000.0 * (1.0 / a - 1.0 / b))
            deltas.append(d_rr_ms)
    if not deltas:
        return 0.0
    return sum(deltas) / len(deltas)


def _count_excursions(samples: Sequence[float], baseline: float, direction: str) -> int:
    """Count contiguous runs of ≥_EXCURSION_MIN_SAMPLES samples that
    are ≥_EXCURSION_BPM_DELTA bpm above (direction='up') or below
    ('down') baseline."""
    if baseline <= 0 or len(samples) < _EXCURSION_MIN_SAMPLES:
        return 0
    threshold = baseline + (_EXCURSION_BPM_DELTA if direction == "up" else -_EXCURSION_BPM_DELTA)
    cmp = (lambda x: x >= threshold) if direction == "up" else (lambda x: x <= threshold and x > 0)
    count = 0
    run = 0
    for s in samples:
        if cmp(s):
            run += 1
        else:
            if run >= _EXCURSION_MIN_SAMPLES:
                count += 1
            run = 0
    if run >= _EXCURSION_MIN_SAMPLES:
        count += 1
    return count


def _hist_stats(samples: Sequence[float]) -> Dict[str, Optional[float]]:
    """Histogram-based features the UCI CTG preprocessor expects."""
    s = [v for v in samples if v and v > 0]
    if not s:
        return {k: None for k in (
            "hist_width", "hist_min", "hist_max", "hist_peaks", "hist_zeroes",
            "hist_mode", "hist_mean", "hist_median", "hist_variance", "hist_tendency",
        )}
    s_sorted = sorted(s)
    mean = sum(s) / len(s)
    n = len(s)
    return {
        "hist_min": float(s_sorted[0]),
        "hist_max": float(s_sorted[-1]),
        "hist_width": float(s_sorted[-1] - s_sorted[0]),
        "hist_mean": round(mean, 1),
        "hist_median": float(s_sorted[n // 2]),
        "hist_mode": float(s_sorted[n // 2]),  # crude — no-bin true mode
        "hist_variance": round(sum((v - mean) ** 2 for v in s) / max(n - 1, 1), 2),
        "hist_peaks": None,    # would need a derivative-based detector
        "hist_zeroes": None,
        "hist_tendency": None,
    }


def analyze(fhr_raw: Optional[Sequence[float]], duration_min: float = 1.0) -> Dict[str, Any]:
    """Compute the dawes_redman block fetal_health adapter expects.

    `fhr_raw` is the per-tick FHR estimate stream the abdomen monitor
    emits — typically 40 Hz raw, but the stateful Render analyzer
    decimates to 1 Hz so this expects either rate (we treat each
    sample as one observation regardless of fs).

    `duration_min` is the wall-clock duration of the buffer — used
    only to convert raw counts to per-minute rates. Mobile sends ~20 s
    windows so this defaults to ~0.33; pass the real value when
    available.

    Returns a dict whose keys match `FetalHealthAdapter._FEATURE_MAP`.
    Fields the simple analyzer can't compute are returned as None so
    the trained UCI preprocessor's imputer covers them."""
    samples: List[float] = []
    if fhr_raw is not None:
        for v in fhr_raw:
            try:
                fv = float(v)
                if 50 <= fv <= 220:    # physiological plausibility band
                    samples.append(fv)
            except (TypeError, ValueError):
                continue

    n = len(samples)
    if n < 30:
        # Too few samples to compute anything meaningful — return a
        # near-empty block so the adapter's median imputer fills the
        # whole row from training data.
        return {
            "samples": n,
            "analysis_ready": False,
            "baseline_fhr": 0.0,
            "stv_ms": 0.0,
            "accelerations": 0,
            "decelerations": 0,
            "accelerations_per_min": 0.0,
            "light_decelerations": 0,
            "severe_decelerations": 0,
            "prolonged_decelerations": 0,
            "abnormal_stv_pct": None,
            "ltv_ms": None,
            "abnormal_ltv_pct": None,
            "criteria_met": False,
            **_hist_stats([]),
        }

    baseline = _trimmed_baseline(samples)
    stv_ms = _stv(samples)
    accels = _count_excursions(samples, baseline, "up")
    decels = _count_excursions(samples, baseline, "down")
    duration_min = max(duration_min, n / 60.0)  # use sample-derived min if window arg low
    criteria_met = bool(
        110.0 <= baseline <= 160.0 and stv_ms >= 3.0 and accels >= 1 and decels == 0
    )
    return {
        "samples": n,
        "analysis_ready": True,
        "baseline_fhr": round(baseline, 1),
        "stv_ms": round(stv_ms, 2),
        "accelerations": accels,
        "decelerations": decels,
        "accelerations_per_min": round(accels / duration_min, 2),
        # Simple analyzer doesn't differentiate; map total decels into
        # "light" bucket and leave severe / prolonged for the imputer.
        "light_decelerations": decels,
        "severe_decelerations": None,
        "prolonged_decelerations": None,
        "abnormal_stv_pct": None,
        "ltv_ms": None,
        "abnormal_ltv_pct": None,
        "criteria_met": criteria_met,
        **_hist_stats(samples),
    }

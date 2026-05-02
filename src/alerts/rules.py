"""
Pure alert rule engine over telemetry snapshots.

Returns a list of {severity, source, message} dicts. The caller is
responsible for de-duplicating and persisting via insert_alert().
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _get(d: Optional[dict], *path, default=None):
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
    return cur if cur is not None else default


def evaluate(snapshot: Dict[str, Any], thresholds: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Evaluate clinical-rule alerts on a snapshot. `thresholds` optionally
    overrides per-vital cutoffs (typically pulled from a CarePlan).

    severity scale: 1–10. Frontend treats 8+ as critical, 5–7 high, 3–4 watch.
    """
    out: List[Dict[str, Any]] = []
    t = thresholds or {}

    spo2 = _get(snapshot, "vitals", "spo2")
    spo2_min = t.get("spo2_min", 90)
    if isinstance(spo2, (int, float)) and spo2 < spo2_min:
        out.append({
            "severity": 7 if spo2 >= 85 else 9,
            "source": "spo2_low",
            "message": f"SpO₂ {spo2:.0f}% (threshold {spo2_min}%)",
        })

    hr = _get(snapshot, "vitals", "heart_rate")
    hr_min = t.get("hr_min", 45)
    hr_max = t.get("hr_max", 130)
    if isinstance(hr, (int, float)):
        if hr > hr_max:
            out.append({
                "severity": 6 if hr <= 150 else 8,
                "source": "hr_high",
                "message": f"Heart rate {hr:.0f} bpm (threshold {hr_max})",
            })
        elif hr < hr_min:
            out.append({
                "severity": 7 if hr >= 35 else 9,
                "source": "hr_low",
                "message": f"Heart rate {hr:.0f} bpm (threshold {hr_min})",
            })

    rr = _get(snapshot, "vitals", "breathing_rate")
    rr_max = t.get("rr_max", 25)
    if isinstance(rr, (int, float)) and rr > rr_max:
        out.append({
            "severity": 5,
            "source": "rr_high",
            "message": f"Respiratory rate {rr:.0f} rpm (threshold {rr_max})",
        })

    decel = _get(snapshot, "fetal", "dawes_redman", "decelerations")
    if isinstance(decel, str) and decel.lower() == "late":
        out.append({
            "severity": 9,
            "source": "fetal_late_decel",
            "message": "Late fetal decelerations detected — escalate immediately.",
        })

    pots_flag = _get(snapshot, "imu_derived", "pots", "pots_flag")
    if pots_flag:
        out.append({
            "severity": 4,
            "source": "pots_flag",
            "message": "Postural orthostatic tachycardia indicators present.",
        })

    poor_posture = _get(snapshot, "imu", "poor_posture")
    if poor_posture:
        out.append({
            "severity": 2,
            "source": "posture_poor",
            "message": f"Sustained poor posture: {_get(snapshot, 'imu', 'posture_label', default='deviation')}.",
        })

    return out

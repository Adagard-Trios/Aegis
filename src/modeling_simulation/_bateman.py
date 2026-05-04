"""
Two-compartment Bateman PK/PD primitive.

Centralised here so the live SSE path (app.py), the cardiac twin, and
the maternal-fetal twin all use the SAME constants and the SAME formula.
Anything that touches the patient's drug state should go through these
helpers — that way the live overlay and a what-if simulation against the
same drug + dose produce identical numbers.
"""
from __future__ import annotations

import math
from typing import Tuple


# Per-drug PK constants — mirror app.py exactly.
# k_abs = absorption rate, k_el_normal = elimination rate (Normal Metabolizer)
DRUG_KINETICS = {
    "labetalol": (0.4, 0.25),
    "oxytocin":  (0.8, 0.45),
}

# Pharmacodynamic effect coefficients (per 100 mg dose at full effect_curve)
DRUG_EFFECTS = {
    # drug -> (delta_hr_bpm, contractions_active_threshold)
    "labetalol": (-15.0, None),       # negative HR effect
    "oxytocin":  (+5.0,  0.15),       # mild HR + contraction trigger
}


def k_el_for(drug: str, cyp2d6_status: str = "Normal Metabolizer") -> Tuple[float, float]:
    """Return (k_abs, k_el) for a drug, applying the CYP2D6 modulation
    that the live SSE path uses (Poor Metabolizer slows clearance to 60%)."""
    drug_norm = (drug or "").strip().lower()
    k_abs, k_el_normal = DRUG_KINETICS.get(drug_norm, (0.5, 0.3))
    k_el = k_el_normal * (0.6 if cyp2d6_status == "Poor Metabolizer" else 1.0)
    return k_abs, k_el


def effect_curve(t: float, k_abs: float, k_el: float) -> float:
    """Two-compartment Bateman effect curve, clipped to [0, 1].

    `t` is hours since the bolus (the live SSE path uses arbitrary "sim
    time" units — we keep the same convention so values match exactly)."""
    if t <= 0:
        return 0.0
    if abs(k_abs - k_el) > 1e-6:
        c = (k_abs / (k_abs - k_el)) * (math.exp(-k_el * t) - math.exp(-k_abs * t))
    else:
        # Limit case k_abs == k_el — degenerate, use the analytical limit
        c = k_abs * t * math.exp(-k_abs * t)
    return max(0.0, min(1.0, c))


def hr_delta_for(drug: str, dose_mg: float, eff: float) -> float:
    """Heart-rate delta in bpm for a given drug + dose at effect level eff (0..1)."""
    drug_norm = (drug or "").strip().lower()
    delta_per_100mg, _ = DRUG_EFFECTS.get(drug_norm, (0.0, None))
    return delta_per_100mg * eff * (dose_mg / 100.0)


def contractions_active(drug: str, dose_mg: float, eff: float) -> bool:
    """For uterotonics: whether (effect × dose-fraction) crosses the
    contraction-activation threshold."""
    drug_norm = (drug or "").strip().lower()
    _, threshold = DRUG_EFFECTS.get(drug_norm, (0.0, None))
    if threshold is None:
        return False
    return eff * (dose_mg / 100.0) > threshold

"""
Cardiac digital twin.

Tracks a per-patient cardiac state (HR baseline + HRV + active drug
boluses + their elapsed time) and lets callers either advance it tick-
by-tick (live SSE path) or simulate a what-if trajectory forward
without mutating the live state (planning endpoints).

State shape (also what the snapshot store persists):

    {
        "hr_bpm": 72.0,            # current heart rate
        "hrv_rmssd": 38.0,         # current RMSSD
        "boluses": [               # list of active drug boluses
            {"drug": "labetalol", "dose_mg": 50, "elapsed_h": 0.42}
        ],
        "drug_effects": {          # current effect curve per drug
            "labetalol": 0.61
        },
        "cyp2d6_status": "Normal Metabolizer",
    }
"""
from __future__ import annotations

import time
import threading
from typing import Any, Dict, Iterator, List, Optional, Tuple

from src.modeling_simulation._bateman import (
    contractions_active,   # noqa: F401  re-export for symmetry
    effect_curve,
    hr_delta_for,
    k_el_for,
)


# Tunable defaults — used both at construction and when reset() is called.
DEFAULT_HR_BPM = 72.0
DEFAULT_HRV_RMSSD = 38.0


class CardiacTwin:
    """Per-patient cardiac twin.

    A singleton-per-patient store is kept by `get_cardiac_twin()` so the
    live SSE loop and any what-if call against the same patient share
    the same drug-bolus state. `simulate()` always works on a *copy* of
    the live state so what-ifs don't mutate the real timeline.
    """

    def __init__(self, patient_id: str = "default"):
        self.patient_id = patient_id
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        """Wipe to baseline. Useful in tests + when a new session starts."""
        with self._lock:
            self.hr_bpm = DEFAULT_HR_BPM
            self.hrv_rmssd = DEFAULT_HRV_RMSSD
            self.boluses: List[Dict[str, Any]] = []
            self.cyp2d6_status = "Normal Metabolizer"

    # ── Public API ───────────────────────────────────────────────────

    def current_state(self) -> Dict[str, Any]:
        with self._lock:
            return self._snapshot()

    def add_bolus(self, drug: str, dose_mg: float) -> None:
        """Register a new drug bolus. Effect starts at t=0 + the next tick
        will begin advancing it."""
        with self._lock:
            self.boluses.append({"drug": drug.strip().lower(), "dose_mg": float(dose_mg), "elapsed_h": 0.0})

    def set_cyp2d6(self, status: str) -> None:
        with self._lock:
            self.cyp2d6_status = status

    def tick(self, dt_s: float, drug_inputs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Advance the twin by `dt_s` seconds.

        `drug_inputs` (optional): list of {drug, dose_mg} dicts to add as
        new boluses BEFORE this tick advances. Lets the live SSE loop
        push the same medicate calls it already handles, without going
        through add_bolus separately.
        """
        with self._lock:
            if drug_inputs:
                for b in drug_inputs:
                    self.boluses.append({
                        "drug": b["drug"].strip().lower(),
                        "dose_mg": float(b["dose_mg"]),
                        "elapsed_h": 0.0,
                    })

            self.hr_bpm = DEFAULT_HR_BPM    # reset to baseline before re-applying
            self.hrv_rmssd = DEFAULT_HRV_RMSSD
            dt_h = dt_s / 3600.0
            survivors: List[Dict[str, Any]] = []
            for b in self.boluses:
                b["elapsed_h"] = b.get("elapsed_h", 0.0) + dt_h
                k_abs, k_el = k_el_for(b["drug"], self.cyp2d6_status)
                eff = effect_curve(b["elapsed_h"], k_abs, k_el)
                self.hr_bpm += hr_delta_for(b["drug"], b["dose_mg"], eff)
                # Drop boluses that have fully washed out + are at least 3 h old
                if not (b["elapsed_h"] > 3.0 and eff < 0.005):
                    survivors.append(b)
            self.boluses = survivors
            return self._snapshot()

    def simulate(
        self,
        scenario_inputs: Optional[Dict[str, Any]] = None,
        treatment_steps: Optional[List[Dict[str, Any]]] = None,
        horizon_min: int = 60,
        step_s: int = 60,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """Project forward `horizon_min` minutes WITHOUT mutating the live twin.

        scenario_inputs (optional): {hr_bpm, hrv_rmssd, cyp2d6_status} —
        starting overrides on the cloned state.

        treatment_steps (optional): list of {t_min, drug, dose_mg} —
        boluses scheduled to fire at the given offset from t=0.

        Returns a list of (t_seconds, state_dict) sampled every step_s.
        Caller charts it as a trajectory.
        """
        scenario_inputs = scenario_inputs or {}
        steps = list(treatment_steps or [])

        # Clone the live state so mutations stay local to this simulation.
        sim = CardiacTwin(self.patient_id)
        with self._lock:
            sim.hr_bpm = float(scenario_inputs.get("hr_bpm", self.hr_bpm))
            sim.hrv_rmssd = float(scenario_inputs.get("hrv_rmssd", self.hrv_rmssd))
            sim.cyp2d6_status = scenario_inputs.get("cyp2d6_status", self.cyp2d6_status)
            # Carry forward the patient's currently-active boluses so we
            # don't pretend they're untreated when projecting forward.
            sim.boluses = [dict(b) for b in self.boluses]

        # Sort treatment steps by t_min so we can fire them at the right tick
        steps.sort(key=lambda s: float(s.get("t_min", 0)))
        next_step_idx = 0

        out: List[Tuple[float, Dict[str, Any]]] = []
        total_steps = max(1, int((horizon_min * 60) / step_s))
        elapsed_s = 0
        for _ in range(total_steps + 1):
            # Apply any boluses due at or before this tick
            new_boluses: List[Dict[str, Any]] = []
            while next_step_idx < len(steps) and float(steps[next_step_idx].get("t_min", 0)) * 60 <= elapsed_s:
                s = steps[next_step_idx]
                new_boluses.append({"drug": s["drug"], "dose_mg": float(s["dose_mg"])})
                next_step_idx += 1
            state = sim.tick(step_s, drug_inputs=new_boluses or None)
            out.append((float(elapsed_s), state))
            elapsed_s += step_s
        return out

    # ── Internal ─────────────────────────────────────────────────────

    def _snapshot(self) -> Dict[str, Any]:
        drug_effects: Dict[str, float] = {}
        for b in self.boluses:
            k_abs, k_el = k_el_for(b["drug"], self.cyp2d6_status)
            drug_effects[b["drug"]] = round(effect_curve(b["elapsed_h"], k_abs, k_el), 4)
        return {
            "hr_bpm": round(self.hr_bpm, 1),
            "hrv_rmssd": round(self.hrv_rmssd, 1),
            "boluses": [dict(b) for b in self.boluses],
            "drug_effects": drug_effects,
            "cyp2d6_status": self.cyp2d6_status,
            "ts": time.time(),
        }


# ── Singleton-per-patient registry ───────────────────────────────────

_twins: Dict[str, CardiacTwin] = {}
_twins_lock = threading.Lock()


def get_cardiac_twin(patient_id: str = "default") -> CardiacTwin:
    with _twins_lock:
        if patient_id not in _twins:
            _twins[patient_id] = CardiacTwin(patient_id)
        return _twins[patient_id]

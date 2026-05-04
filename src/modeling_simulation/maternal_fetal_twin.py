"""
Maternal-fetal digital twin.

Tracks the maternal-fetal unit's state — fetal heart rate baseline,
uterine activity (0..1 contraction intensity), Bishop cervix score,
and the active oxytocin infusion. Mirrors how the live SSE path
already drives oxytocin → contraction onset, but in a stateful object
that can be ticked forward without touching the live snapshot.

State:
    {
        "fhr_bpm": 140.0,             # fetal heart rate baseline
        "uterine_activity": 0.32,     # 0=quiet 1=full contraction
        "cervix_score": 4,            # Bishop (0..10) — clinical readiness
        "oxytocin_dose_mg": 50.0,     # most recent oxytocin bolus (mg)
        "contractions_per_10min": 3,  # derived from uterine_activity
        "boluses": [{...}],           # active drug list (matches CardiacTwin shape)
        "ts": <epoch>
    }
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from src.modeling_simulation._bateman import (
    contractions_active,
    effect_curve,
    k_el_for,
)


DEFAULT_FHR_BPM = 140.0
DEFAULT_CERVIX_SCORE = 4
DEFAULT_UTERINE_ACTIVITY = 0.0


class MaternalFetalTwin:
    """Per-patient maternal-fetal twin.

    Same simulate() / tick() / current_state() contract as CardiacTwin.
    The key new behaviour is uterine_activity is driven by the active
    oxytocin bolus's effect_curve, and contractions_per_10min is derived
    from sustained uterine_activity over the previous tick window.
    """

    def __init__(self, patient_id: str = "default"):
        self.patient_id = patient_id
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.fhr_bpm = DEFAULT_FHR_BPM
            self.uterine_activity = DEFAULT_UTERINE_ACTIVITY
            self.cervix_score = DEFAULT_CERVIX_SCORE
            self.boluses: List[Dict[str, Any]] = []
            self.cyp2d6_status = "Normal Metabolizer"
            # Rolling counter of contraction onsets in the last 10 min
            self._contraction_history: List[float] = []   # epoch timestamps

    # ── Public API ───────────────────────────────────────────────────

    def current_state(self) -> Dict[str, Any]:
        with self._lock:
            return self._snapshot()

    def add_bolus(self, drug: str, dose_mg: float) -> None:
        with self._lock:
            self.boluses.append({"drug": drug.strip().lower(), "dose_mg": float(dose_mg), "elapsed_h": 0.0})

    def set_cyp2d6(self, status: str) -> None:
        with self._lock:
            self.cyp2d6_status = status

    def tick(self, dt_s: float, drug_inputs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        with self._lock:
            if drug_inputs:
                for b in drug_inputs:
                    self.boluses.append({
                        "drug": b["drug"].strip().lower(),
                        "dose_mg": float(b["dose_mg"]),
                        "elapsed_h": 0.0,
                    })

            self.fhr_bpm = DEFAULT_FHR_BPM
            self.uterine_activity = 0.0
            now = time.time()
            dt_h = dt_s / 3600.0
            survivors: List[Dict[str, Any]] = []
            was_contracting = self.uterine_activity > 0.5

            for b in self.boluses:
                b["elapsed_h"] = b.get("elapsed_h", 0.0) + dt_h
                k_abs, k_el = k_el_for(b["drug"], self.cyp2d6_status)
                eff = effect_curve(b["elapsed_h"], k_abs, k_el)

                if b["drug"] == "oxytocin":
                    # Oxytocin drives uterine activity proportional to
                    # effect × dose-fraction; threshold gates real contractions
                    activity = eff * (b["dose_mg"] / 100.0)
                    self.uterine_activity = max(self.uterine_activity, min(1.0, activity))
                    # Mild fetal-HR elevation (matches app.py's +5 bpm overlay)
                    self.fhr_bpm += 5.0 * eff * (b["dose_mg"] / 100.0)
                # (Other drugs could affect FHR too — extend here as needed)

                if not (b["elapsed_h"] > 3.0 and eff < 0.005):
                    survivors.append(b)
            self.boluses = survivors

            # Rising-edge contraction detection — log onsets > threshold
            if self.uterine_activity > 0.5 and not was_contracting:
                self._contraction_history.append(now)
            # Trim history to last 10 minutes
            cutoff = now - 600
            self._contraction_history = [t for t in self._contraction_history if t > cutoff]

            return self._snapshot()

    def simulate(
        self,
        scenario_inputs: Optional[Dict[str, Any]] = None,
        treatment_steps: Optional[List[Dict[str, Any]]] = None,
        horizon_min: int = 60,
        step_s: int = 60,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """Project forward without mutating the live twin. Same shape as
        CardiacTwin.simulate."""
        scenario_inputs = scenario_inputs or {}
        steps = list(treatment_steps or [])

        sim = MaternalFetalTwin(self.patient_id)
        with self._lock:
            sim.fhr_bpm = float(scenario_inputs.get("fhr_bpm", self.fhr_bpm))
            sim.cervix_score = int(scenario_inputs.get("cervix_score", self.cervix_score))
            sim.cyp2d6_status = scenario_inputs.get("cyp2d6_status", self.cyp2d6_status)
            sim.boluses = [dict(b) for b in self.boluses]

        steps.sort(key=lambda s: float(s.get("t_min", 0)))
        next_step_idx = 0
        out: List[Tuple[float, Dict[str, Any]]] = []
        total_steps = max(1, int((horizon_min * 60) / step_s))
        elapsed_s = 0
        for _ in range(total_steps + 1):
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
        return {
            "fhr_bpm": round(self.fhr_bpm, 1),
            "uterine_activity": round(self.uterine_activity, 3),
            "cervix_score": self.cervix_score,
            "contractions_per_10min": len(self._contraction_history),
            "boluses": [dict(b) for b in self.boluses],
            "cyp2d6_status": self.cyp2d6_status,
            "ts": time.time(),
        }


# ── Singleton-per-patient registry ───────────────────────────────────

_twins: Dict[str, MaternalFetalTwin] = {}
_twins_lock = threading.Lock()


def get_maternal_fetal_twin(patient_id: str = "default") -> MaternalFetalTwin:
    with _twins_lock:
        if patient_id not in _twins:
            _twins[patient_id] = MaternalFetalTwin(patient_id)
        return _twins[patient_id]

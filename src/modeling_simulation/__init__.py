"""
src/modeling_simulation — Phase 3 of the agentic upgrade.

Organ-level digital twin modules + simulation primitives. Each twin
exposes a uniform contract:

    twin.current_state() -> dict
    twin.tick(dt_s, drug_inputs={}) -> next_state
    twin.simulate(scenario_inputs, horizon_min) -> Iterator[(t, state)]

Live tick path: the SSE telemetry loop calls `tick()` once per second
with the current drug bolus state, so the twin tracks the patient in
real time and persists snapshots via twin_state_store.

What-if path: the `/api/digital-twin/scenario` and `/api/digital-twin/plan`
routes call `simulate()` to project forward without touching the live
twin state — the result is a list of (t, state) for the frontend to chart.

The Bateman PK/PD constants here intentionally match the values already
used in app.py's SSE overlay so the live path and the simulation path
produce the same numbers for the same drug + dose.
"""

from src.modeling_simulation.cardiac_twin import CardiacTwin, get_cardiac_twin
from src.modeling_simulation.maternal_fetal_twin import MaternalFetalTwin, get_maternal_fetal_twin
from src.modeling_simulation.twin_state_store import (
    write_twin_snapshot,
    read_twin_timeline,
    insert_simulation_run,
    get_simulation_run,
    list_simulation_runs,
)

__all__ = [
    "CardiacTwin",
    "MaternalFetalTwin",
    "get_cardiac_twin",
    "get_maternal_fetal_twin",
    "write_twin_snapshot",
    "read_twin_timeline",
    "insert_simulation_run",
    "get_simulation_run",
    "list_simulation_runs",
]

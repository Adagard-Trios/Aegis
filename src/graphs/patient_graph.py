"""
src/graphs/patient_graph.py

Patient-facing LangGraph workflow using individual specialty subgraphs.

Topology (Phase 1.6 — selective fan-out):

    START
      → patient_information_fetcher
      → sync_initialization
        ↓ (parallel split)
      ├→ continuous_monitoring → audience_aware_compiler
      └→ orchestrator
           ↓
         planning_node              ← rule-based gating
           ↓ (conditional fan-out)
         [cardiology|pulmonary|neurology|dermatology|gyno|ocular]_expert
           ↓ (fan-in — only the selected ones contribute)
         general_physician
           ↓
         audience_aware_compiler → END / loop

Previously orchestrator → ALL 6 experts unconditionally. The planner
inspects `continuous_monitoring_data` and writes `selected_specialties`
to state; the conditional edge routes to only those specialty nodes.
General Physician fan-in still works because LangGraph waits only on
the actually-invoked predecessors.
"""
from langgraph.graph import StateGraph, START, END

from src.states.patient_state import PatientWorkflowState
from src.nodes.patient_node import (
    patient_information_fetcher,
    sync_initialization,
    continuous_monitoring,
    orchestrator,
    planning_node,
    planner_router,
    cardiology_expert,
    pulmonary_expert,
    neurology_expert,
    dermatology_expert,
    gyno_urologist_expert,
    occulometric_expert,
    general_physician,
    audience_aware_compiler,
)

# All expert node IDs — the planner_router returns a subset of these.
expert_nodes = [
    "cardiology_expert",
    "pulmonary_expert",
    "neurology_expert",
    "dermatology_expert",
    "gyno_urologist_expert",
    "occulometric_expert",
]

# =============================================================================
# GRAPH BUILDER
# =============================================================================
builder = StateGraph(PatientWorkflowState)

# ── Initialization ────────────────────────────────────────────────────────
builder.add_node("patient_information_fetcher", patient_information_fetcher)
builder.add_node("sync_initialization", sync_initialization)

# ── Parallel Tracks (The Loop) ────────────────────────────────────────────
builder.add_node("continuous_monitoring", continuous_monitoring)
builder.add_node("orchestrator", orchestrator)

# ── Planning (Phase 1.6) ──────────────────────────────────────────────────
builder.add_node("planning_node", planning_node)

# ── Expert Swarm (now using individual specialty graphs) ──────────────────
builder.add_node("cardiology_expert", cardiology_expert)
builder.add_node("pulmonary_expert", pulmonary_expert)
builder.add_node("neurology_expert", neurology_expert)
builder.add_node("dermatology_expert", dermatology_expert)
builder.add_node("gyno_urologist_expert", gyno_urologist_expert)
builder.add_node("occulometric_expert", occulometric_expert)

# ── Synthesis & Output ───────────────────────────────────────────────────
builder.add_node("general_physician", general_physician)
builder.add_node("audience_aware_compiler", audience_aware_compiler)

# =============================================================================
# EDGES
# =============================================================================

# Start → Fetcher → Sync
builder.add_edge(START, "patient_information_fetcher")
builder.add_edge("patient_information_fetcher", "sync_initialization")

# Sync branches to both Continuous Monitoring and Orchestrator
builder.add_edge("sync_initialization", "continuous_monitoring")
builder.add_edge("sync_initialization", "orchestrator")

# Orchestrator → Planner → conditional fan-out to selected experts.
# planner_router returns a list of node IDs; LangGraph fans out to all
# of them. Unselected experts simply don't run; general_physician's
# fan-in waits only on the invoked predecessors.
builder.add_edge("orchestrator", "planning_node")
builder.add_conditional_edges(
    "planning_node",
    planner_router,
    {n: n for n in expert_nodes},
)

# ALL Experts fan-in to the General Physician (only the invoked ones
# actually fire; LangGraph handles partial fan-in correctly).
for node in expert_nodes:
    builder.add_edge(node, "general_physician")

# GP + Continuous Monitoring → Compiler
builder.add_edge("general_physician", "audience_aware_compiler")
builder.add_edge("continuous_monitoring", "audience_aware_compiler")

# The loop/end is handled by Command inside audience_aware_compiler

# =============================================================================
# COMPILE
# =============================================================================
patient_workflow = builder.compile(
    interrupt_before=["orchestrator", "general_physician"]
)

graph = patient_workflow

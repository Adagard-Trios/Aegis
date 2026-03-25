"""
src/graphs/patient_graph.py

Patient-facing LangGraph workflow using individual specialty subgraphs.
"""
from langgraph.graph import StateGraph, START, END

from src.states.patient_state import PatientWorkflowState
from src.nodes.patient_node import (
    patient_information_fetcher,
    sync_initialization,
    continuous_monitoring,
    orchestrator,
    cardiology_expert,
    pulmonary_expert,
    neurology_expert,
    dermatology_expert,
    gyno_urologist_expert,
    occulometric_expert,
    general_physician,
    audience_aware_compiler
)

# All expert nodes that fan out from the orchestrator
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

# Orchestrator fans out to ALL Expert nodes in parallel
for node in expert_nodes:
    builder.add_edge("orchestrator", node)

# ALL Experts fan-in to the General Physician
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
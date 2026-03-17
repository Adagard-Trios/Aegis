from langgraph.graph import StateGraph, START, END

from src.states.patient_state import PatientWorkflowState
from src.nodes.patient_node import (
    patient_information_fetcher,
    sync_initialization,
    continuous_monitoring,
    orchestrator,
    psychiatric_expert,
    dermatology_expert,
    cardiology_expert,
    pulmonary_expert,
    gyno_urologist_expert,
    environment_context_expert,
    occulometric_expert,
    infectious_disease_expert,
    general_physician,
    audience_aware_compiler
)

# List of all 8 experts mirroring the visual diagram
expert_nodes = [
    "psychiatric_expert",
    "dermatology_expert",
    "cardiology_expert",
    "pulmonary_expert",
    "gyno_urologist_expert",
    "environment_context_expert",
    "occulometric_expert",
    "infectious_disease_expert"
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

# ── Expert Swarm ──────────────────────────────────────────────────────────
for node in expert_nodes:
    builder.add_node(node, globals()[node])

# ── Synthesis & Output ───────────────────────────────────────────────────
builder.add_node("general_physician", general_physician)
builder.add_node("audience_aware_compiler", audience_aware_compiler)

# =============================================================================
# EDGES
# =============================================================================

# Start to Fetcher
builder.add_edge(START, "patient_information_fetcher")

# Fetcher to sync node
builder.add_edge("patient_information_fetcher", "sync_initialization")

# Sync node branches to both Continuous Monitoring and Orchestrator (Parallel Workflow)
builder.add_edge("sync_initialization", "continuous_monitoring")
builder.add_edge("sync_initialization", "orchestrator")

# Orchestrator uses Parallel Function Calling to all Experts
for node in expert_nodes:
    builder.add_edge("orchestrator", node)

# ALL Experts fan-in to the General Physician (Master Synthesizer)
for node in expert_nodes:
    builder.add_edge(node, "general_physician")

# Both the final GP synthesis AND the Continuous Monitoring feed into the Compiler
builder.add_edge("general_physician", "audience_aware_compiler")
builder.add_edge("continuous_monitoring", "audience_aware_compiler")

# NOTE: The loop back from audience_aware_compiler -> sync_initialization 
# OR audience_aware_compiler -> END is handled dynamically by the LangGraph Command inside the node.

# =============================================================================
# COMPILE WITH HITL INTERRUPTS
# =============================================================================
# Interrupting before the Orchestrator or General Physician allows a human 
# to review data or update context mid-flight.
patient_workflow = builder.compile(
    interrupt_before=["orchestrator", "general_physician"]
)

# Export name expected by `langgraph.json`
graph = patient_workflow
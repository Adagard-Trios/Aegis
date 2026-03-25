"""
src/graphs/doctor_graph.py

Doctor-facing LangGraph workflow using individual specialty subgraphs.
"""
from langgraph.graph import START, StateGraph

from src.nodes.doctor_node import (
    audience_aware_router,
    cardiology_expert,
    pulmonary_expert,
    neurology_expert,
    dermatology_expert,
    general_physician,
    gyno_urologist_expert,
    nfc_data_loader,
    occulometric_expert,
    orchestrator,
    patient_information_selector,
    sync_initialization,
)
from src.states.doctor_state import DoctorWorkflowState

# All expert nodes
expert_nodes = [
    "cardiology_expert",
    "pulmonary_expert",
    "neurology_expert",
    "dermatology_expert",
    "gyno_urologist_expert",
    "occulometric_expert",
]

builder = StateGraph(DoctorWorkflowState)

# ── Nodes ─────────────────────────────────────────────────────────────────
builder.add_node("nfc_data_loader", nfc_data_loader)
builder.add_node("patient_information_selector", patient_information_selector)
builder.add_node("sync_initialization", sync_initialization)

builder.add_node("orchestrator", orchestrator)

builder.add_node("cardiology_expert", cardiology_expert)
builder.add_node("pulmonary_expert", pulmonary_expert)
builder.add_node("neurology_expert", neurology_expert)
builder.add_node("dermatology_expert", dermatology_expert)
builder.add_node("gyno_urologist_expert", gyno_urologist_expert)
builder.add_node("occulometric_expert", occulometric_expert)

builder.add_node("general_physician", general_physician)
builder.add_node("audience_aware_router", audience_aware_router)

# ── Edges ─────────────────────────────────────────────────────────────────
builder.add_edge(START, "nfc_data_loader")
builder.add_edge("nfc_data_loader", "patient_information_selector")
builder.add_edge("patient_information_selector", "sync_initialization")

builder.add_edge("sync_initialization", "orchestrator")

for node in expert_nodes:
    builder.add_edge("orchestrator", node)

for node in expert_nodes:
    builder.add_edge(node, "general_physician")

builder.add_edge("general_physician", "audience_aware_router")


# The loop/end is handled by Command inside audience_aware_router

doctor_workflow = builder.compile(interrupt_before=["orchestrator", "general_physician"])

graph = doctor_workflow
doctor_graph = doctor_workflow

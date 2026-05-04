"""
Collaborative diagnosis graph.

Topology:

    __start__
        │
        ▼
    planner_node              ─── decides which specialty graphs to run
        │                          (recorded in selected_specialties; the
        │                           parent patient_graph is responsible
        │                           for actually fanning out to those)
        ▼
    disease_proposer_node     ─── LLM proposes 3-7 common candidates
        │
        ▼
    rare_disease_agent_node   ─── KB lookup adds rare candidates
        │
        ▼
    related_disease_finder    ─── KB-similarity expansion of confusables
        │
        ▼
    background_agents_node    ─── LLM attaches per-candidate evidence
        │
        ▼
    skeptic_node              ─── LLM disconfirms; pulls scores down
        │
        ▼
    diagnosis_agent_node      ─── final ranking + recommended next tests
        │
        ▼
    __end__

The graph is intentionally linear (not a DAG with parallel branches) for
two reasons: (1) each node refines the candidate set produced by the
previous one, so they have a strict data dependency; (2) sequential
ordering keeps the reasoning trace readable in the UI. If we later want
parallel background agents (per-candidate fan-out), we can split that
node without restructuring the rest.

The compiled graph is exported as `graph` so langgraph.json can register
it the same way as the existing specialty graphs.
"""

from __future__ import annotations
from langgraph.graph import StateGraph, END

from src.states.complex_diagnosis_state import ComplexDiagnosisState
from src.nodes.complex_diagnosis_node import (
    planner_node,
    disease_proposer_node,
    rare_disease_agent_node,
    related_disease_finder_node,
    background_agents_node,
    skeptic_node,
    diagnosis_agent_node,
)


def build_complex_diagnosis_graph() -> StateGraph:
    """Construct (uncompiled) the collaborative diagnosis graph."""
    builder = StateGraph(ComplexDiagnosisState)

    builder.add_node("planner", planner_node)
    builder.add_node("disease_proposer", disease_proposer_node)
    builder.add_node("rare_disease_agent", rare_disease_agent_node)
    builder.add_node("related_disease_finder", related_disease_finder_node)
    builder.add_node("background_agents", background_agents_node)
    builder.add_node("skeptic", skeptic_node)
    builder.add_node("diagnosis_agent", diagnosis_agent_node)

    builder.add_edge("__start__", "planner")
    builder.add_edge("planner", "disease_proposer")
    builder.add_edge("disease_proposer", "rare_disease_agent")
    builder.add_edge("rare_disease_agent", "related_disease_finder")
    builder.add_edge("related_disease_finder", "background_agents")
    builder.add_edge("background_agents", "skeptic")
    builder.add_edge("skeptic", "diagnosis_agent")
    builder.add_edge("diagnosis_agent", END)

    return builder


# Pre-compiled instance, matching the convention used by the per-specialty
# graphs (so app.py and langgraph.json can both `from ... import graph`).
graph = build_complex_diagnosis_graph().compile()

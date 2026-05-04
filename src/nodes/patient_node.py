"""
src/nodes/patient_node.py

Patient workflow nodes — uses individual specialty graphs
instead of the old shared expert_subgraph.
"""
import os
from typing_extensions import Literal
from typing import List

from langchain_core.messages import HumanMessage, AIMessage, get_buffer_string
from langgraph.types import Command
from langgraph.graph import END

from src.llms.groqllm import GroqLLM
from src.states.patient_state import (
    PatientWorkflowState,
    GeneralPhysicianDiagnosis,
    AudienceAwareRouting
)
from src.utils.utils import get_today_str
# Reuse the rule-based planner from the complex_diagnosis graph so we
# have ONE source of truth for "given this snapshot, which specialties
# are worth invoking" — same logic for both the patient_graph fan-out
# and the complex_diagnosis_graph fan-out.
from src.nodes.complex_diagnosis_node import planner_node as _shared_planner

# Import individual specialty compiled graphs
from src.graphs.cardiology_graph import graph as cardiology_graph
from src.graphs.pulmonary_graph import graph as pulmonary_graph
from src.graphs.neurology_graph import graph as neurology_graph
from src.graphs.dermatology_graph import graph as dermatology_graph
from src.graphs.gynecology_graph import graph as gynecology_graph
from src.graphs.ocular_graph import graph as ocular_graph
from src.graphs.general_physician_graph import graph as gp_graph

# Registry: domain string → compiled graph
_SPECIALTY_GRAPHS = {
    "Cardiology": cardiology_graph,
    "Pulmonary": pulmonary_graph,
    "Neurology": neurology_graph,
    "Dermatology": dermatology_graph,
    "Obstetrics": gynecology_graph,
    "Ocular": ocular_graph,
    "General Physician": gp_graph,
}

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = GroqLLM().get_llm()
    return _model


# =============================================================================
# INITIALIZATION NODES
# =============================================================================

def patient_information_fetcher(state: PatientWorkflowState):
    """Initializes the workflow by fetching the user profile and baseline data."""
    return {
        "patient_info": "Standard patient baseline loaded. No severe prior conditions.",
        "messages": [AIMessage(content="Patient profile loaded and verified.")]
    }


def sync_initialization(state: PatientWorkflowState):
    """Pass-through node to synchronize the parallel start tracks."""
    return {}


# =============================================================================
# CONTINUOUS LOOP NODES
# =============================================================================

def continuous_monitoring(state: PatientWorkflowState):
    """Simulates continuous ingestion of high-fidelity data from the wearable vest."""
    telemetry = {
        "heart_rate": 82,
        "spO2": 98,
        "temperature": 36.6,
        "posture": "upright",
        "respiratory_rate": 16
    }
    return {"continuous_monitoring_data": telemetry}


def orchestrator(state: PatientWorkflowState):
    """
    Prepares telemetry for the parallel experts.
    *HITL INTERRUPT POINT*: Allows human to inject context or override routing.
    """
    if state.get("human_feedback"):
        msg = f"Orchestrator context updated by user/physician: {state['human_feedback']}"
        return {"messages": [AIMessage(content=msg)]}

    return {"messages": [AIMessage(content="Orchestrator dispatching telemetry to Expert Agents.")]}


# =============================================================================
# EXPERT AGENT NODES (Using Individual Specialty Graphs)
# =============================================================================

def _invoke_specialty_graph(domain: str, state: PatientWorkflowState) -> dict:
    """Invoke a specialty-specific compiled graph with the patient's state.

    Returns both the expert analysis AND the subgraph's reasoning trace,
    so the patient_graph's `traces` accumulator gets the full per-
    specialty chain of reasoning (information_retrieval +
    interpretation_generation steps) — not just the final summary."""
    compiled_graph = _SPECIALTY_GRAPHS.get(domain)

    if compiled_graph is None:
        return {
            "expert_analyses": [{
                "expert_domain": domain,
                "clinical_findings": f"No graph available for {domain}",
                "anomaly_detected": False,
                "confidence_score": 0.0,
            }]
        }

    subgraph_initial_state = {
        "expert_domain": domain,
        "sensor_telemetry": state.get("continuous_monitoring_data", {}),
        "shared_context": {
            "patient_base": state.get("patient_info", ""),
            "human_feedback": state.get("human_feedback", ""),
            "patient_id": "patient_001",
        },
        "messages": [],
        "traces": [],
    }

    result = compiled_graph.invoke(subgraph_initial_state)
    out: dict = {
        "expert_analyses": [result.get("final_expert_analysis", {})],
    }
    # Forward subgraph traces into the patient state so the UI sees one
    # unified reasoning trace covering the whole run.
    sub_traces = result.get("traces") or []
    if sub_traces:
        out["traces"] = sub_traces
    return out


# =============================================================================
# PLANNER (Phase 1.6) — selective specialty fan-out
# =============================================================================

def planning_node(state: PatientWorkflowState) -> dict:
    """Decide which specialty experts to actually invoke for this run.

    Reuses the rule-based planner from `src/nodes/complex_diagnosis_node`
    so we have one source of truth. The shared planner expects
    `sensor_telemetry` on its state; we adapt by feeding the patient
    state's `continuous_monitoring_data` under that key.

    Returns `selected_specialties` + `planner_rationale` — the conditional
    edge in patient_graph reads `selected_specialties` to fan out only
    to the matching expert nodes."""
    adapted_state = {
        "sensor_telemetry": state.get("continuous_monitoring_data") or {},
        "ml_outputs": {},
    }
    out = _shared_planner(adapted_state)
    selected = out.get("selected_specialties") or ["Cardiology", "General Physician"]
    rationale = out.get("planner_rationale") or "Default workup"

    msg = AIMessage(content=f"Planner selected {len(selected)} specialty graph(s): {', '.join(selected)}")
    update: dict = {
        "selected_specialties": selected,
        "planner_rationale": rationale,
        "messages": [msg],
    }
    if out.get("traces"):
        update["traces"] = out["traces"]
    return update


# Mapping from planner output (specialty NAMES) to the graph node IDs
# that the conditional edge router emits. Keep this in sync with the
# expert_nodes list in patient_graph.py.
SPECIALTY_NODE_MAP = {
    "Cardiology": "cardiology_expert",
    "Pulmonary": "pulmonary_expert",
    "Neurology": "neurology_expert",
    "Dermatology": "dermatology_expert",
    "Obstetrics": "gyno_urologist_expert",
    "Ocular": "occulometric_expert",
    # General Physician is the synthesiser, not a fan-out specialist
    "General Physician": None,
}


def planner_router(state: PatientWorkflowState) -> List[str]:
    """LangGraph conditional-edge router.

    Returns the list of expert-node IDs to invoke based on
    `selected_specialties`. Always includes at least one node — falls
    back to cardiology if the planner returned nothing actionable, so
    the graph never deadlocks on an empty fan-out."""
    selected = state.get("selected_specialties") or []
    nodes: List[str] = []
    for s in selected:
        node_id = SPECIALTY_NODE_MAP.get(s)
        if node_id:
            nodes.append(node_id)
    return nodes or ["cardiology_expert"]


def cardiology_expert(state: PatientWorkflowState):
    return _invoke_specialty_graph("Cardiology", state)


def pulmonary_expert(state: PatientWorkflowState):
    return _invoke_specialty_graph("Pulmonary", state)


def neurology_expert(state: PatientWorkflowState):
    return _invoke_specialty_graph("Neurology", state)


def dermatology_expert(state: PatientWorkflowState):
    return _invoke_specialty_graph("Dermatology", state)


def gyno_urologist_expert(state: PatientWorkflowState):
    return _invoke_specialty_graph("Obstetrics", state)


def occulometric_expert(state: PatientWorkflowState):
    return _invoke_specialty_graph("Ocular", state)


# =============================================================================
# SYNTHESIS & ROUTING NODES
# =============================================================================

def general_physician(state: PatientWorkflowState):
    """Apex master synthesizer evaluating all expert viewpoints."""
    structured_model = _get_model().with_structured_output(GeneralPhysicianDiagnosis)

    expert_reports_str = "\n".join([str(e) for e in state.get('expert_analyses', [])])
    prompt = (
        f"Synthesize the following expert reports into a final patient diagnosis.\n"
        f"Expert Data:\n{expert_reports_str}\n"
        f"Date: {get_today_str()}"
    )

    response = structured_model.invoke([HumanMessage(content=prompt)])

    if response is None:
        return {"physician_diagnosis": "Synthesis failed."}

    return {
        "physician_diagnosis": response.holistic_evaluation,
        "messages": [AIMessage(content="General Physician synthesis complete.")]
    }


def audience_aware_compiler(state: PatientWorkflowState) -> Command[Literal["sync_initialization", "__end__"]]:
    """
    Compiles results for patient/clinical dashboards and handles the continuous
    looping back to the orchestrator layer if the session remains active.
    """
    structured_model = _get_model().with_structured_output(AudienceAwareRouting)

    prompt = (
        f"Format this diagnosis for both patient UI and clinical dashboards: "
        f"{state.get('physician_diagnosis')}\n"
        f"Set routing_flag to 'loop' to continue monitoring, or 'stop' to end.\n"
        f"Date: {get_today_str()}"
    )

    response = structured_model.invoke([HumanMessage(content=prompt)])

    if response is None:
        return Command(goto=END, update={"compiled_results": {}})

    if response.routing_flag == "loop":
        return Command(
            goto="sync_initialization",
            update={"compiled_results": response.dict()}
        )
    else:
        return Command(
            goto=END,
            update={"compiled_results": response.dict()}
        )
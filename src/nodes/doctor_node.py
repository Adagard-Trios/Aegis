"""
src/nodes/doctor_node.py

Doctor workflow nodes — uses individual specialty graphs
instead of the old shared expert_subgraph.
"""
from datetime import datetime
from typing_extensions import Literal

from src.llms.groqllm import GroqLLM
from langchain_core.messages import HumanMessage, AIMessage, get_buffer_string
from langgraph.types import Command
from langgraph.graph import END

from src.states.doctor_state import (
    DoctorWorkflowState,
    NFCInitialization,
    GeneralPhysicianReview,
    AudienceAwareCompilation
)
from src.utils.utils import get_today_str

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

def nfc_data_loader(state: DoctorWorkflowState):
    structured_model = _get_model().with_structured_output(NFCInitialization)
    prompt = f"Extract NFC token and ID. Date: {get_today_str()}"
    response = structured_model.invoke([HumanMessage(content=prompt)])

    if response is None:
        return {"nfc_payload": {}}

    return {
        "nfc_payload": response.dict(),
        "messages": [AIMessage(content="NFC tap verified.")]
    }


def patient_information_selector(state: DoctorWorkflowState):
    record = {"patient_history": "Standard baseline loaded."}
    return {
        "patient_record": record,
        "messages": [AIMessage(content="Patient EHR retrieved.")]
    }


def sync_initialization(state: DoctorWorkflowState):
    return {}


# =============================================================================
# CONTINUOUS LOOP NODES
# =============================================================================

def continuous_monitoring(state: DoctorWorkflowState):
    telemetry = {"heart_rate": 88, "spO2": 97, "temperature": 36.8}
    return {"continuous_monitoring_data": telemetry}


def orchestrator(state: DoctorWorkflowState):
    return {"messages": [AIMessage(content="Orchestrator dispatching data.")]}


# =============================================================================
# EXPERT NODES (Using Individual Specialty Graphs)
# =============================================================================

def _invoke_specialty_graph(domain: str, state: DoctorWorkflowState) -> dict:
    """Invoke a specialty-specific compiled graph with the doctor's state."""
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
            "orchestrator_hitl_feedback": state.get("orchestrator_hitl_feedback", ""),
            "patient_id": "patient_001",
        },
        "messages": [],
    }

    result = compiled_graph.invoke(subgraph_initial_state)
    return {"expert_analyses": [result.get("final_expert_analysis", {})]}


def cardiology_expert(state: DoctorWorkflowState):
    return _invoke_specialty_graph("Cardiology", state)


def pulmonary_expert(state: DoctorWorkflowState):
    return _invoke_specialty_graph("Pulmonary", state)


def neurology_expert(state: DoctorWorkflowState):
    return _invoke_specialty_graph("Neurology", state)


def dermatology_expert(state: DoctorWorkflowState):
    return _invoke_specialty_graph("Dermatology", state)


def gyno_urologist_expert(state: DoctorWorkflowState):
    return _invoke_specialty_graph("Obstetrics", state)


def occulometric_expert(state: DoctorWorkflowState):
    return _invoke_specialty_graph("Ocular", state)


# =============================================================================
# SYNTHESIS AND ROUTING NODES
# =============================================================================

def general_physician(state: DoctorWorkflowState):
    structured_model = _get_model().with_structured_output(GeneralPhysicianReview)
    expert_reports = "\n".join([str(e) for e in state.get('expert_analyses', [])])
    prompt = f"Synthesize reports into final diagnosis: {expert_reports}\nDate: {get_today_str()}"

    response = structured_model.invoke([HumanMessage(content=prompt)])
    if response is None:
        return {"final_clinical_review": "Synthesis failed."}

    return {
        "final_clinical_review": response.holistic_diagnosis,
        "messages": [AIMessage(content="Apex clinical synthesis complete.")]
    }


def audience_aware_router(state: DoctorWorkflowState) -> Command[Literal["sync_initialization", "__end__"]]:
    structured_model = _get_model().with_structured_output(AudienceAwareCompilation)
    prompt = f"Compile UI data based on this diagnosis: {state.get('final_clinical_review')}\nDate: {get_today_str()}"

    response = structured_model.invoke([HumanMessage(content=prompt)])
    if response is None:
        return Command(goto=END, update={"compiled_results": {}})

    if response.routing_flag == "loop":
        return Command(goto="sync_initialization", update={"compiled_results": response.dict()})
    else:
        return Command(goto=END, update={"compiled_results": response.dict()})
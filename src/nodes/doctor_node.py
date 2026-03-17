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

# IMPORTANT: Import the compiled expert subgraph
from src.graphs.expert_graph import expert_subgraph

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

    return {"nfc_payload": response.dict(), "messages": [AIMessage(content=f"NFC tap verified.")]}

def patient_information_selector(state: DoctorWorkflowState):
    record = {"patient_history": "Standard baseline loaded."}
    return {"patient_record": record, "messages": [AIMessage(content="Patient EHR retrieved.")]}

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
# EXPERT NODES (Triggering Subgraphs)
# =============================================================================
def _invoke_expert_subgraph(domain: str, state: DoctorWorkflowState) -> dict:
    """Wrapper to map Doctor workflow state into the Expert Subgraph state."""
    subgraph_initial_state = {
        "expert_domain": domain,
        "sensor_telemetry": state.get("continuous_monitoring_data", {}),
        # Pass any doctor specific overrides into the expert's shared context
        "shared_context": {"orchestrator_hitl_feedback": state.get("orchestrator_hitl_feedback", "")},
        "messages": []
    }
    
    result = expert_subgraph.invoke(subgraph_initial_state)
    return {"expert_analyses": [result["final_expert_analysis"]]}

def psychiatric_expert(state: DoctorWorkflowState): return _invoke_expert_subgraph("Psychiatric", state)
def dermatology_expert(state: DoctorWorkflowState): return _invoke_expert_subgraph("Dermatology", state)
def cardiology_expert(state: DoctorWorkflowState): return _invoke_expert_subgraph("Cardiology", state)
def pulmonary_expert(state: DoctorWorkflowState): return _invoke_expert_subgraph("Pulmonary", state)
def gyno_urologist_expert(state: DoctorWorkflowState): return _invoke_expert_subgraph("Gyno/Urologist", state)
def environment_context_expert(state: DoctorWorkflowState): return _invoke_expert_subgraph("Environment Context", state)
def occulometric_expert(state: DoctorWorkflowState): return _invoke_expert_subgraph("Occulometric", state)
def infectious_disease_expert(state: DoctorWorkflowState): return _invoke_expert_subgraph("Infectious Disease", state)
def environment_context_expert(state: DoctorWorkflowState): return _invoke_expert_subgraph("Environment Context", state)
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
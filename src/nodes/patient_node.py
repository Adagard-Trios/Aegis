import os
from typing_extensions import Literal

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

def patient_information_fetcher(state: PatientWorkflowState):
    """Initializes the workflow by fetching the user profile and baseline data."""
    # Simulating a database fetch
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
    """Simulates the continuous ingestion of high-fidelity data from the wearable vest."""
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
# EXPERT AGENT NODES (Triggering Subgraphs)
# =============================================================================

def _invoke_expert_subgraph(domain: str, state: PatientWorkflowState) -> dict:
    """Wrapper to map Patient workflow state into the Expert Subgraph state."""
    subgraph_initial_state = {
        "expert_domain": domain,
        "sensor_telemetry": state.get("continuous_monitoring_data", {}),
        "shared_context": {
            "patient_base": state.get("patient_info", ""),
            "human_feedback": state.get("human_feedback", "")
        },
        "messages": []
    }
    
    # Run the dedicated expert subgraph natively
    result = expert_subgraph.invoke(subgraph_initial_state)
    
    # Return exactly the format expected by the operator.add in PatientWorkflowState
    return {"expert_analyses": [result.get("final_expert_analysis", {})]}

def psychiatric_expert(state: PatientWorkflowState): 
    return _invoke_expert_subgraph("Psychiatric", state)
def dermatology_expert(state: PatientWorkflowState): 
    return _invoke_expert_subgraph("Dermatology", state)

def cardiology_expert(state: PatientWorkflowState): 
    return _invoke_expert_subgraph("Cardiology", state)

def pulmonary_expert(state: PatientWorkflowState): 
    return _invoke_expert_subgraph("Pulmonary", state)

def gyno_urologist_expert(state: PatientWorkflowState): 
    return _invoke_expert_subgraph("Gyno/Urologist", state)

def infectious_disease_expert(state: PatientWorkflowState): 
    return _invoke_expert_subgraph("Infectios_disease", state)

def environment_context_expert(state: PatientWorkflowState):
    return _invoke_expert_subgraph("Environment_Context", state)

def occulometric_expert(state: PatientWorkflowState): 
    return _invoke_expert_subgraph("Occulometric", state)


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
    
    print("[General Physician] PROMPT:", prompt)
    response = structured_model.invoke([HumanMessage(content=prompt)])
    print("[General Physician] STRUCTURED RESPONSE:", response)

    if response is None:
        return {"physician_diagnosis": "Synthesis failed."}

    return {
        "physician_diagnosis": response.holistic_evaluation,
        "messages": [AIMessage(content="General Physician synthesis complete.")]
    }

def audience_aware_compiler(state: PatientWorkflowState) -> Command[Literal["sync_initialization", "__end__"]]:
    """
    Compiles results for patient/clinical dashboards and handles the continuous looping 
    back to the orchestrator layer if the session remains active.
    """
    structured_model = _get_model().with_structured_output(AudienceAwareRouting)
    
    prompt = (
        f"Format this diagnosis for both patient UI and clinical dashboards: "
        f"{state.get('physician_diagnosis')}\n"
        f"Set routing_flag to 'loop' to continue monitoring, or 'stop' to end.\n"
        f"Date: {get_today_str()}"
    )
    
    print("[Compiler] PROMPT:", prompt)
    response = structured_model.invoke([HumanMessage(content=prompt)])
    print("[Compiler] STRUCTURED RESPONSE:", response)

    if response is None:
        return Command(goto=END, update={"compiled_results": {}})

    # LangGraph Command routing for continuous monitoring
    print("[Compiler] STRUCTURED RESPONSE:", response)

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
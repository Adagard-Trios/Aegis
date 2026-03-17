from typing import Annotated, Sequence, Optional
from typing import TypedDict # Standard typing, NOT typing_extensions
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# Safe reducer for the expert swarm
def reduce_analyses(left: list[dict] | None, right: list[dict] | None) -> list[dict]:
    if left is None: left = []
    if right is None: right = []
    return left + right

# Added total=False and simplified types to list/dict for safe UI parsing
class PatientWorkflowState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    patient_info: str 
    continuous_monitoring_data: dict 
    
    # Safe reducer applied
    expert_analyses: Annotated[list[dict], reduce_analyses]
    
    human_feedback: Optional[str] 
    compiled_results: dict 
    physician_diagnosis: str 

class WorkflowOutputState(TypedDict, total=False):
    compiled_results: dict 
    physician_diagnosis: str
    messages: Annotated[Sequence[BaseMessage], add_messages]

class HumanInTheLoopClarification(BaseModel):
    requires_intervention: bool = Field(description="Whether the AI requires a human doctor to review or clarify the current data.")
    prompt_to_human: str = Field(description="The specific question, anomaly, or data point presented to the human for review.")
    override_decision: str = Field(description="The decision or updated context provided by the human reviewer.")

class ExpertEvaluation(BaseModel):
    expert_domain: str = Field(description="The specialty of the expert agent (e.g., Cardiology, Pulmonary, Occulometric).")
    clinical_findings: str = Field(description="Detailed findings based on the specific sensor data and patient context.")
    anomaly_detected: bool = Field(description="Flag indicating if an anomaly or critical condition was detected by this expert.")

class AudienceAwareRouting(BaseModel):
    patient_facing_summary: str = Field(description="A plain-language, easily understandable health summary for the user's daily wellness tracking.")
    clinical_dashboard_data: str = Field(description="High-fidelity, nuanced medical reports and traces for the professional medical UI.")
    routing_flag: str = Field(description="Determines if the system should 'loop' back for continuous monitoring or 'stop'.")

class GeneralPhysicianDiagnosis(BaseModel):
    holistic_evaluation: str = Field(description="A comprehensive evaluation weighing all distinct viewpoints from the active experts.")
    compounded_threats: str = Field(description="Identification of any compounded medical threats based on cross-evaluating expert data.")
    action_plan: str = Field(description="Immediate triage steps, recommendations, or continuous monitoring adjustments.")
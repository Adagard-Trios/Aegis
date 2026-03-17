import operator
from typing import Annotated, List, Sequence, Dict, Any, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class DoctorWorkflowState(TypedDict):
    """
    Core state for the clinical wearable's multi-agent Doctor Workflow.

    Tracks the progression of data initiated by a doctor (e.g., via NFC tap),
    parallel continuous monitoring, parallel expert agent analysis, 
    human-in-the-loop feedback at multiple stages, and the compiled medical output.
    """
    # Standard LangGraph message history
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Initial Data Loading Phase
    nfc_payload: Dict[str, Any]
    patient_record: Dict[str, Any]
    
    # Continuous Monitoring (Foetal, ECG, Temp, SpO2, Respiratory)
    continuous_monitoring_data: Dict[str, Any] 
    
    # Parallel Expert Analyses (aggregated via operator.add)
    # Includes: Psychiatric, Dermatology, Cardiology, Pulmonary, Gyno/Urologist, 
    # Environment Context, Occulometric, Infectious Disease
    expert_analyses: Annotated[List[Dict[str, Any]], operator.add]
    
    # Human-in-the-loop (HITL) overrides/clarifications
    orchestrator_hitl_feedback: Optional[str]
    physician_hitl_feedback: Optional[str]
    
    # Compiled results from the Audience Aware Router
    compiled_results: Dict[str, Any]
    
    # Final synthesized diagnosis and review by the General Physician agent/human
    final_clinical_review: str 

class DoctorWorkflowOutputState(TypedDict):
    """
    Output state representing the final package delivered to the clinical UI/dashboard.
    """
    patient_record: Dict[str, Any]
    compiled_results: Dict[str, Any]
    final_clinical_review: str
    messages: Annotated[Sequence[BaseMessage], add_messages]


## --- Structured Output Schemas ---

class NFCInitialization(BaseModel):
    """Schema for the initial NFC Data Loader phase."""
    auth_token: str = Field(description="Authentication token from the doctor's NFC badge or device.")
    patient_id: str = Field(description="Extracted patient identifier from the NFC tap.")
    device_status: str = Field(description="Hardware status of the wearable vest upon connection.")

class HumanInTheLoopIntervention(BaseModel):
    """Schema for human-in-the-loop interventions (used by both Orchestrator and General Physician)."""
    requires_doctor_input: bool = Field(
        description="Whether the AI requires the human doctor to review, approve, or clarify."
    )
    context_prompt: str = Field(
        description="The specific medical anomaly or routing decision presented to the doctor."
    )
    doctor_override_notes: str = Field(
        description="The clinical notes, decisions, or updated context provided by the human doctor."
    )

class ExpertEvaluation(BaseModel):
    """Schema for the individual specialized Expert Agents evaluating the telemetry."""
    expert_domain: str = Field(
        description="The specialty of the expert agent (e.g., Cardiology, Infectious Disease, Occulometric)."
    )
    clinical_findings: str = Field(
        description="Detailed findings based on the specific sensor data (e.g., ESP32-S3 streams)."
    )
    anomaly_detected: bool = Field(
        description="Flag indicating if a critical condition was detected requiring immediate attention."
    )
    confidence_score: float = Field(
        description="Agent's confidence in its diagnostic findings (0.0 to 1.0)."
    )

class AudienceAwareCompilation(BaseModel):
    """Schema for the Audience Aware Results Compiler/Router."""
    raw_telemetry_links: List[str] = Field(
        description="Pointers to the raw time-series data (ECG traces, acoustic files) for UI rendering."
    )
    aggregated_expert_summary: str = Field(
        description="A synthesized summary of all parallel expert agent findings."
    )
    routing_flag: str = Field(
        description="Determines if data loops back to the Orchestrator or proceeds to the General Physician."
    )

class GeneralPhysicianReview(BaseModel):
    """Schema for the apex General Physician Agent's final clinical output."""
    holistic_diagnosis: str = Field(
        description="A comprehensive clinical evaluation weighing all distinct expert viewpoints."
    )
    compounded_threats: List[str] = Field(
        description="Identification of any compounded medical threats based on cross-evaluating expert data."
    )
    recommended_intervention: str = Field(
        description="Immediate medical triage steps, prescriptions, or continuous monitoring adjustments."
    )
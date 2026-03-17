import operator
from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ExpertSubgraphState(TypedDict):
    """
    State contract used by the expert subgraph.

    This is intentionally aligned to what `patient_node.py` / `doctor_node.py` send
    (`expert_domain`, `sensor_telemetry`, `shared_context`) and what they expect back
    (`final_expert_analysis`).
    """

    # Standard LangGraph message history
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Inputs
    expert_domain: str
    sensor_telemetry: Dict[str, Any]
    shared_context: Dict[str, Any]

    # Output
    final_expert_analysis: Dict[str, Any]

    # Optional debug/status fields
    error_message: Optional[str]

    # (Optional) accumulate intermediate traces if needed later
    traces: Annotated[List[Dict[str, Any]], operator.add]

import operator
from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ExpertSubgraphState(TypedDict):
    """
    Shared state contract used by ALL specialty subgraphs.

    Flow: information_retrieval populates tool_results →
          interpretation_generation reads tool_results + produces final_expert_analysis.
    """

    # Standard LangGraph message history
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Inputs (set by the parent graph before invocation)
    expert_domain: str
    sensor_telemetry: Dict[str, Any]
    shared_context: Dict[str, Any]

    # Intermediate (populated by information_retrieval node)
    tool_results: Dict[str, str]

    # Output (populated by interpretation_generation node)
    final_expert_analysis: Dict[str, Any]

    # Optional debug/status fields
    error_message: Optional[str]

    # Accumulate intermediate traces
    traces: Annotated[List[Dict[str, Any]], operator.add]

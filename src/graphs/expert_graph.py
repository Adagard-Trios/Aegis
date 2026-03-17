from langgraph.graph import StateGraph

from src.nodes.expert_subgraph_node import create_expert_subgraph


def create_expert_workflow() -> StateGraph:
    return create_expert_subgraph()


# Default compiled expert subgraph used by patient/doctor workflows
expert_subgraph = create_expert_workflow().compile()


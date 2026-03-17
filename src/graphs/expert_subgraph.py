from langgraph.graph import StateGraph

from src.nodes.expert_subgraph_node import create_expert_subgraph


def create_expert_workflow(_expert_type: str) -> StateGraph:
    # Right now the expert type is driven by the runtime state (`expert_domain`).
    # We still keep per-expert compiled exports for `langgraph.json` parity.
    return create_expert_subgraph()


def get_expert_subgraph(expert_type: str):
    workflow = create_expert_workflow(expert_type)
    return workflow.compile()


# Exports expected by `langgraph.json`
psychiatric_expert_graph = get_expert_subgraph("Psychiatric")
cardiology_expert_graph = get_expert_subgraph("Cardiology")
gastroenterological_expert_graph = get_expert_subgraph("Gastroenterological")
gynecological_expert_graph = get_expert_subgraph("Gynecological")
ent_expert_graph = get_expert_subgraph("ENT")
ocular_expert_graph = get_expert_subgraph("Ocular")
dermatology_expert_graph = get_expert_subgraph("Dermatology")
dental_expert_graph = get_expert_subgraph("Dental")
pulmonology_expert_graph = get_expert_subgraph("Pulmonology")
neurology_expert_graph = get_expert_subgraph("Neurology")
orthopedic_expert_graph = get_expert_subgraph("Orthopedic")
pharmacist_expert_graph = get_expert_subgraph("Pharmacist")
endocrinologist_expert_graph = get_expert_subgraph("Endocrinologist")
nephrology_expert_graph = get_expert_subgraph("Nephrology")
infectious_disease_expert_graph = get_expert_subgraph("Infectious Disease")

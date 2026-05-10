"""
src/graphs/pulmonary_graph.py
Pulmonology Expert subgraph — respiratory, SpO2.
"""
from src.graphs.graph_factory import build_expert_graph

graph = build_expert_graph("Pulmonology Expert").compile()

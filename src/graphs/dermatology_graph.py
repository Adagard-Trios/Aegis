"""
src/graphs/dermatology_graph.py
Dermatology Expert subgraph — skin temp, thermal mapping.
"""
from src.graphs.graph_factory import build_expert_graph

graph = build_expert_graph("Dermatology Expert").compile()

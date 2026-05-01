"""
src/graphs/ocular_graph.py
Ocular Expert subgraph — pupil assessment, IOP.
"""
from src.graphs.graph_factory import build_expert_graph

graph = build_expert_graph("Ocular Expert").compile()

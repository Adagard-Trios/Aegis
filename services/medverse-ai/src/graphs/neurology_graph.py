"""
src/graphs/neurology_graph.py
Neurology Expert subgraph — IMU, fall risk, sleep.
"""
from src.graphs.graph_factory import build_expert_graph

graph = build_expert_graph("Neurology Expert").compile()

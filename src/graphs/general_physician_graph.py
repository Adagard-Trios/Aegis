"""
src/graphs/general_physician_graph.py
General Physician subgraph — vitals summary, cross-specialty flags, history.
"""
from src.graphs.graph_factory import build_expert_graph

graph = build_expert_graph("General Physician").compile()

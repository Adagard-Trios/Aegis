"""
src/graphs/cardiology_graph.py
Cardiology Expert subgraph — ECG, BP, biomarkers.
"""
from src.graphs.graph_factory import build_expert_graph

graph = build_expert_graph("Cardiology Expert").compile()

"""
src/graphs/gynology_graph.py
Obstetrics/Gynecology Expert subgraph — CTG, FHR, uterine.
"""
from src.graphs.graph_factory import build_expert_graph

graph = build_expert_graph("Obstetrics Expert").compile()

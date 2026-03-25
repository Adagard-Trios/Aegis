"""General Physician node — re-exports from graph_factory."""
from src.graphs.graph_factory import _make_information_retrieval, _make_interpretation_generation

information_retrieval = _make_information_retrieval("General Physician")
interpretation_generation = _make_interpretation_generation("General Physician")

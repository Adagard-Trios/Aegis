"""
src/ml — runtime adapters for the ML models that live under models/.

Each adapter is a thin, dependency-light class that:
  • loads weights from MODELS_DIR / <subpath> when available,
  • exposes a uniform `is_loaded` / `predict` / `embed` API,
  • gracefully returns a `None` or sentinel when weights are absent,
    so the LangGraph nodes can always run.
"""
import os

MODELS_DIR = os.environ.get(
    "MEDVERSE_MODELS_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models")),
)

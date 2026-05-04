"""Export the latest trained preterm_labour model as a runtime pickle.

See `models/fetal_health/export_runtime.py` for the full design rationale —
identical pattern, different runtime path. The estimator's preprocessor +
model are extracted from the pipeline-local ModelEstimator class and
re-saved as a plain dict so the runtime adapter at
src/ml/preterm_labour_adapter.py can load it without importing the
pipeline's namespace.

Output: ${MEDVERSE_MODELS_DIR}/obstetrics/preterm_labour/model.pkl
"""
from __future__ import annotations

import os
import pickle
import sys

_PIPELINE_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PIPELINE_ROOT not in sys.path:
    sys.path.insert(0, _PIPELINE_ROOT)
_REPO_ROOT = os.path.abspath(os.path.join(_PIPELINE_ROOT, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.append(_REPO_ROOT)

from src.utils.main_utils import load_object  # noqa: E402

RUNTIME_SUBPATH = "obstetrics/preterm_labour/model.pkl"


def _latest_estimator_path() -> str:
    artifacts_dir = os.path.join(_PIPELINE_ROOT, "artifacts")
    if not os.path.isdir(artifacts_dir):
        raise FileNotFoundError(f"No artifacts/ at {artifacts_dir} - run `python main.py` first.")
    runs = sorted(d for d in os.listdir(artifacts_dir)
                  if os.path.isdir(os.path.join(artifacts_dir, d)))
    if not runs:
        raise FileNotFoundError("No training runs in artifacts/")
    p = os.path.join(artifacts_dir, runs[-1], "model_trainer", "trained_model", "model.pkl")
    if not os.path.exists(p):
        raise FileNotFoundError(f"Trained model not at {p}")
    return p


def main() -> None:
    src_path = _latest_estimator_path()
    print(f"[export_runtime] loading: {src_path}")
    estimator = load_object(src_path)
    bundle = {
        "preprocessor": getattr(estimator, "preprocessor", None),
        "model": getattr(estimator, "model", None),
    }
    if bundle["model"] is None:
        raise RuntimeError("Loaded estimator has no .model attribute")

    base = os.environ.get("MEDVERSE_MODELS_DIR",
                          os.path.abspath(os.path.join(_REPO_ROOT, "models")))
    dst = os.path.join(base, RUNTIME_SUBPATH)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as fh:
        pickle.dump(bundle, fh)
    print(f"[export_runtime] wrote: {dst} ({os.path.getsize(dst) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()

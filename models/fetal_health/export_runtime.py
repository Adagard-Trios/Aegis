"""Export the latest trained fetal_health model as a runtime pickle.

Usage:

    cd models/fetal_health
    python main.py             # train (writes artifacts/<ts>/.../model.pkl)
    python export_runtime.py   # extract + copy to runtime path

The training pipeline saves a `ModelEstimator(preprocessor, model)`
whose class lives in this pipeline's `src.utils.ml_utils.model.estimator`.
The runtime adapter at `src/ml/fetal_health_adapter.py` can't import
that class (different `src` package), so this script extracts the
sklearn-native preprocessor + model out of the estimator and re-saves
them as a plain dict that any process can load with stdlib pickle.

Output goes to:
    ${MEDVERSE_MODELS_DIR}/obstetrics/fetal_health/model.pkl

(MEDVERSE_MODELS_DIR defaults to <repo>/models, so the runtime artefact
sits at models/obstetrics/fetal_health/model.pkl alongside the existing
per-pipeline directories without colliding.)
"""
from __future__ import annotations

import os
import pickle
import sys

# Make the pipeline's local `src` package the resolved one so we can
# unpickle the ModelEstimator (which references this pipeline's class path).
_PIPELINE_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PIPELINE_ROOT not in sys.path:
    sys.path.insert(0, _PIPELINE_ROOT)

# Repo-root pipeline_utils for any download-on-demand imports
_REPO_ROOT = os.path.abspath(os.path.join(_PIPELINE_ROOT, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.append(_REPO_ROOT)

from src.utils.main_utils import load_object  # noqa: E402  (after sys.path tweak)


RUNTIME_SUBPATH = "obstetrics/fetal_health/model.pkl"


def _latest_estimator_path() -> str:
    """Find the most-recent trained model.pkl under artifacts/<ts>/."""
    artifacts_dir = os.path.join(_PIPELINE_ROOT, "artifacts")
    if not os.path.isdir(artifacts_dir):
        raise FileNotFoundError(
            f"No artifacts/ at {artifacts_dir} - run `python main.py` first."
        )
    runs = sorted(d for d in os.listdir(artifacts_dir)
                  if os.path.isdir(os.path.join(artifacts_dir, d)))
    if not runs:
        raise FileNotFoundError("No training runs in artifacts/")
    latest = runs[-1]
    estimator_path = os.path.join(
        artifacts_dir, latest, "model_trainer", "trained_model", "model.pkl"
    )
    if not os.path.exists(estimator_path):
        raise FileNotFoundError(f"Trained model not at {estimator_path}")
    return estimator_path


def _runtime_root() -> str:
    """Where the runtime adapter expects to find weights."""
    base = os.environ.get(
        "MEDVERSE_MODELS_DIR",
        os.path.abspath(os.path.join(_REPO_ROOT, "models")),
    )
    return base


def main() -> None:
    src_path = _latest_estimator_path()
    print(f"[export_runtime] loading: {src_path}")
    estimator = load_object(src_path)

    bundle = {
        "preprocessor": getattr(estimator, "preprocessor", None),
        "model": getattr(estimator, "model", None),
    }
    if bundle["model"] is None:
        raise RuntimeError("Loaded estimator has no .model attribute - bad export source")

    dst_path = os.path.join(_runtime_root(), RUNTIME_SUBPATH)
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "wb") as fh:
        pickle.dump(bundle, fh)

    size_kb = os.path.getsize(dst_path) / 1024
    print(f"[export_runtime] wrote: {dst_path} ({size_kb:.1f} KB)")
    print("[export_runtime] runtime adapter will pick this up on next get_fetal_health() call.")


if __name__ == "__main__":
    main()

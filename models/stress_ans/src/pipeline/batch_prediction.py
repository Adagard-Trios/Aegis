"""Score a CSV with the latest trained model.

    python -m src.pipeline.batch_prediction --input data.csv --output preds.csv
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import Optional

import pandas as pd

from src.constants import training_pipeline as C
from src.exception.exception import MedVerseException
from src.logging.logger import logging
from src.utils.main_utils import load_object


class BatchPrediction:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or self._latest_model_path()

    @staticmethod
    def _latest_model_path() -> str:
        candidates = sorted(
            glob.glob(
                os.path.join(
                    C.ARTIFACT_DIR, "*", C.MODEL_TRAINER_DIR_NAME,
                    C.MODEL_TRAINER_TRAINED_MODEL_DIR, C.MODEL_TRAINER_TRAINED_MODEL_FILE_NAME,
                )
            )
        )
        if not candidates:
            raise FileNotFoundError(
                f"No trained model under {C.ARTIFACT_DIR}/. Run the training pipeline first."
            )
        return candidates[-1]

    def predict_csv(self, input_csv: str, output_csv: str) -> str:
        try:
            df = pd.read_csv(input_csv)
            estimator = load_object(self.model_path)
            preds = estimator.predict(df)
            out = df.copy()
            out["prediction"] = preds
            out.to_csv(output_csv, index=False)
            logging.info(f"BatchPrediction: {input_csv} -> {output_csv} ({len(out)} rows)")
            return output_csv
        except Exception as e:
            raise MedVerseException(e, sys) from e


def _cli() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--model", default=None)
    args = p.parse_args()
    BatchPrediction(model_path=args.model).predict_csv(args.input, args.output)


if __name__ == "__main__":  # pragma: no cover
    _cli()

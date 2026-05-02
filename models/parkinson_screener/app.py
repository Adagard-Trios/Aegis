"""FastAPI service exposing this pipeline's trained model.

POST /predict {"records": [{...}, ...]} -> {"predictions": [...]}.

The router auto-discovers the latest trained model under artifacts/. Mount
this app as a microservice (uvicorn app:app) or wire it into the main
MedVerse backend via httpx if you prefer a single deploy unit.
"""
from __future__ import annotations

import sys
from typing import List, Dict, Any, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.exception.exception import MedVerseException
from src.logging.logger import logging  # noqa: F401
from src.pipeline.batch_prediction import BatchPrediction
from src.utils.main_utils import load_object

app = FastAPI(title="MedVerse model service", version="0.1.0")

_estimator = None


def _get_estimator():
    global _estimator
    if _estimator is None:
        try:
            path = BatchPrediction()._latest_model_path()
            _estimator = load_object(path)
        except Exception as e:
            raise MedVerseException(e, sys) from e
    return _estimator


class PredictRequest(BaseModel):
    records: List[Dict[str, Any]]


class PredictResponse(BaseModel):
    predictions: List[Any]
    model_path: Optional[str] = None


@app.get("/health")
def health() -> dict:
    try:
        path = BatchPrediction()._latest_model_path()
        return {"status": "ok", "model_path": path}
    except FileNotFoundError as e:
        return {"status": "no_model", "detail": str(e)}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    if not req.records:
        raise HTTPException(status_code=400, detail="records cannot be empty")
    df = pd.DataFrame.from_records(req.records)
    est = _get_estimator()
    preds = list(est.predict(df))
    return PredictResponse(predictions=preds)

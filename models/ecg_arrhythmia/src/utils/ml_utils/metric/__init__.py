"""Common ML metrics. Extend per-pipeline if specialised metrics are needed."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class ClassificationMetric:
    f1_score: float
    precision: float
    recall: float
    accuracy: float


def classification_metrics(y_true: Sequence, y_pred: Sequence) -> ClassificationMetric:
    from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score

    return ClassificationMetric(
        f1_score=float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        precision=float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
        recall=float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
        accuracy=float(accuracy_score(y_true, y_pred)),
    )


@dataclass
class RegressionMetric:
    mae: float
    rmse: float
    r2: float


def regression_metrics(y_true: Sequence, y_pred: Sequence) -> RegressionMetric:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    import numpy as _np

    return RegressionMetric(
        mae=float(mean_absolute_error(y_true, y_pred)),
        rmse=float(_np.sqrt(mean_squared_error(y_true, y_pred))),
        r2=float(r2_score(y_true, y_pred)),
    )

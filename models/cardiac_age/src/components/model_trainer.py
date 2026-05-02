"""cardiac_age — ModelTrainer

Source notebook: notebooks/source.ipynb
Notebook architecture: CardiacAgeResNet (ResBlock1D depths [64,128,256,512] + SE), MSELoss regression.

This pipeline currently trains on the PTB-XL metadata (sex, heart_axis flags) features produced by
DataIngestion._load_dataframe(). To upgrade to the notebook's full
architecture you'd extend `_load_dataframe` to return the raw 12-lead ECG 5000 samples @ 100 Hz
and replace `_build_model` with the notebook's PyTorch / Keras model.
"""
from __future__ import annotations

import os
import sys
from typing import Any

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.append(_REPO_ROOT)

from src.entity.config_entity import ModelTrainerConfig
from src.entity.artifact_entity import (
    DataTransformationArtifact,
    ModelTrainerArtifact,
    ClassificationMetricArtifact,
)
from src.exception.exception import MedVerseException
from src.logging.logger import logging
from src.utils.main_utils import load_numpy_array, load_object, save_object
from src.utils.ml_utils.metric import classification_metrics, regression_metrics
from src.utils.ml_utils.model import ModelEstimator


class ModelTrainer:
    def __init__(self, transformation_artifact: DataTransformationArtifact, config: ModelTrainerConfig):
        self.transformation_artifact = transformation_artifact
        self.config = config

    def _build_model(self):
        from sklearn.ensemble import GradientBoostingRegressor
        return GradientBoostingRegressor(
            n_estimators=300, max_depth=5, learning_rate=0.05, random_state=42,
        )

    def _compute_metrics(self, y_true, y_pred) -> ClassificationMetricArtifact:
        # Regression task — pack regression metrics into the existing artifact slots
        # so the template's downstream gate (expected_accuracy on f1_score) keeps
        # working without changing the artifact dataclass.
        m = regression_metrics(y_true, y_pred)
        return ClassificationMetricArtifact(
            f1_score=max(m.r2, 0.0),     # R^2 (clipped to >=0) — proxy for "score"
            precision_score=m.mae,        # mean absolute error
            recall_score=m.rmse,          # root mean squared error
        )

    def initiate_model_trainer(self) -> ModelTrainerArtifact:
        try:
            train_arr = load_numpy_array(self.transformation_artifact.transformed_train_file_path)
            test_arr = load_numpy_array(self.transformation_artifact.transformed_test_file_path)

            x_train, y_train = train_arr[:, :-1], train_arr[:, -1]
            x_test, y_test = test_arr[:, :-1], test_arr[:, -1]

            model = self._build_model()
            model.fit(x_train, y_train)

            train_metric = self._compute_metrics(y_train, model.predict(x_train))
            test_metric = self._compute_metrics(y_test, model.predict(x_test))

            logging.info(
                f"ModelTrainer: r2_test={test_metric.f1_score:.3f} "
                f"mae={test_metric.precision_score:.3f} rmse={test_metric.recall_score:.3f}"
            )

            preprocessor = load_object(self.transformation_artifact.transformed_object_file_path)
            estimator = ModelEstimator(preprocessor=preprocessor, model=model)
            os.makedirs(os.path.dirname(self.config.trained_model_file_path), exist_ok=True)
            save_object(self.config.trained_model_file_path, estimator)

            return ModelTrainerArtifact(
                trained_model_file_path=self.config.trained_model_file_path,
                train_metric_artifact=train_metric,
                test_metric_artifact=test_metric,
            )
        except Exception as e:
            raise MedVerseException(e, sys) from e

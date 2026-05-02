"""Model trainer — fit a model on the transformed arrays.

Override `_build_model` and (optionally) `_compute_metrics` for the model
family this pipeline uses.
"""
from __future__ import annotations

import os
import sys

from src.entity.config_entity import ModelTrainerConfig
from src.entity.artifact_entity import (
    DataTransformationArtifact,
    ModelTrainerArtifact,
    ClassificationMetricArtifact,
)
from src.exception.exception import MedVerseException
from src.logging.logger import logging
from src.utils.main_utils import load_numpy_array, load_object, save_object
from src.utils.ml_utils.metric import classification_metrics
from src.utils.ml_utils.model import ModelEstimator


class ModelTrainer:
    def __init__(self, transformation_artifact: DataTransformationArtifact, config: ModelTrainerConfig):
        self.transformation_artifact = transformation_artifact
        self.config = config

    def _build_model(self):
        """Override in per-pipeline subclass to return a fitted-able estimator."""
        raise NotImplementedError(
            "ModelTrainer._build_model is a stub. Override it to return an "
            "untrained sklearn / torch / lightgbm estimator for this pipeline."
        )

    def _compute_metrics(self, y_true, y_pred) -> ClassificationMetricArtifact:
        m = classification_metrics(y_true, y_pred)
        return ClassificationMetricArtifact(
            f1_score=m.f1_score, precision_score=m.precision, recall_score=m.recall
        )

    def initiate_model_trainer(self) -> ModelTrainerArtifact:
        try:
            train_arr = load_numpy_array(self.transformation_artifact.transformed_train_file_path)
            test_arr = load_numpy_array(self.transformation_artifact.transformed_test_file_path)

            x_train, y_train = train_arr[:, :-1], train_arr[:, -1]
            x_test, y_test = test_arr[:, :-1], test_arr[:, -1]

            model = self._build_model()
            model.fit(x_train, y_train)

            train_pred = model.predict(x_train)
            test_pred = model.predict(x_test)
            train_metric = self._compute_metrics(y_train, train_pred)
            test_metric = self._compute_metrics(y_test, test_pred)

            if test_metric.f1_score < self.config.expected_accuracy:
                logging.warning(
                    f"ModelTrainer: f1={test_metric.f1_score:.3f} below expected "
                    f"{self.config.expected_accuracy:.3f}"
                )
            if abs(train_metric.f1_score - test_metric.f1_score) > self.config.overfit_underfit_threshold:
                logging.warning(
                    f"ModelTrainer: train/test gap "
                    f"{abs(train_metric.f1_score - test_metric.f1_score):.3f} above "
                    f"threshold {self.config.overfit_underfit_threshold:.3f}"
                )

            preprocessor = load_object(self.transformation_artifact.transformed_object_file_path)
            estimator = ModelEstimator(preprocessor=preprocessor, model=model)
            os.makedirs(os.path.dirname(self.config.trained_model_file_path), exist_ok=True)
            save_object(self.config.trained_model_file_path, estimator)

            logging.info(f"ModelTrainer: f1_test={test_metric.f1_score:.3f}")
            return ModelTrainerArtifact(
                trained_model_file_path=self.config.trained_model_file_path,
                train_metric_artifact=train_metric,
                test_metric_artifact=test_metric,
            )
        except Exception as e:
            raise MedVerseException(e, sys) from e

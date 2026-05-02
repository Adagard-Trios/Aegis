"""Per-stage configuration dataclasses, derived from constants.

The TrainingPipelineConfig sets the timestamped run directory; every other
config is anchored to that directory.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime

from src.constants import training_pipeline as C


@dataclass
class TrainingPipelineConfig:
    pipeline_name: str = C.PIPELINE_NAME
    artifact_name: str = C.ARTIFACT_DIR
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))

    @property
    def artifact_dir(self) -> str:
        return os.path.join(self.artifact_name, self.timestamp)


@dataclass
class DataIngestionConfig:
    pipeline_config: TrainingPipelineConfig

    @property
    def data_ingestion_dir(self) -> str:
        return os.path.join(self.pipeline_config.artifact_dir, C.DATA_INGESTION_DIR_NAME)

    @property
    def feature_store_file_path(self) -> str:
        return os.path.join(self.data_ingestion_dir, C.DATA_INGESTION_FEATURE_STORE_DIR, C.DATA_INGESTION_RAW_FILE_NAME)

    @property
    def training_file_path(self) -> str:
        return os.path.join(self.data_ingestion_dir, C.DATA_INGESTION_INGESTED_DIR, C.DATA_INGESTION_TRAIN_FILE_NAME)

    @property
    def testing_file_path(self) -> str:
        return os.path.join(self.data_ingestion_dir, C.DATA_INGESTION_INGESTED_DIR, C.DATA_INGESTION_TEST_FILE_NAME)

    train_test_split_ratio: float = C.DATA_INGESTION_TRAIN_TEST_SPLIT_RATIO


@dataclass
class DataValidationConfig:
    pipeline_config: TrainingPipelineConfig

    @property
    def data_validation_dir(self) -> str:
        return os.path.join(self.pipeline_config.artifact_dir, C.DATA_VALIDATION_DIR_NAME)

    @property
    def valid_train_file_path(self) -> str:
        return os.path.join(self.data_validation_dir, C.DATA_VALIDATION_VALID_DIR, C.DATA_INGESTION_TRAIN_FILE_NAME)

    @property
    def valid_test_file_path(self) -> str:
        return os.path.join(self.data_validation_dir, C.DATA_VALIDATION_VALID_DIR, C.DATA_INGESTION_TEST_FILE_NAME)

    @property
    def invalid_train_file_path(self) -> str:
        return os.path.join(self.data_validation_dir, C.DATA_VALIDATION_INVALID_DIR, C.DATA_INGESTION_TRAIN_FILE_NAME)

    @property
    def invalid_test_file_path(self) -> str:
        return os.path.join(self.data_validation_dir, C.DATA_VALIDATION_INVALID_DIR, C.DATA_INGESTION_TEST_FILE_NAME)

    @property
    def drift_report_file_path(self) -> str:
        return os.path.join(self.data_validation_dir, "report", C.DATA_VALIDATION_DRIFT_REPORT_FILE_NAME)

    schema_file_path: str = C.SCHEMA_FILE_PATH


@dataclass
class DataTransformationConfig:
    pipeline_config: TrainingPipelineConfig

    @property
    def data_transformation_dir(self) -> str:
        return os.path.join(self.pipeline_config.artifact_dir, C.DATA_TRANSFORMATION_DIR_NAME)

    @property
    def transformed_train_file_path(self) -> str:
        return os.path.join(self.data_transformation_dir, C.DATA_TRANSFORMATION_TRANSFORMED_DIR, "train.npy")

    @property
    def transformed_test_file_path(self) -> str:
        return os.path.join(self.data_transformation_dir, C.DATA_TRANSFORMATION_TRANSFORMED_DIR, "test.npy")

    @property
    def transformed_object_file_path(self) -> str:
        return os.path.join(self.data_transformation_dir, C.DATA_TRANSFORMATION_OBJECT_DIR, C.PREPROCESSING_OBJECT_FILE_NAME)


@dataclass
class ModelTrainerConfig:
    pipeline_config: TrainingPipelineConfig

    @property
    def model_trainer_dir(self) -> str:
        return os.path.join(self.pipeline_config.artifact_dir, C.MODEL_TRAINER_DIR_NAME)

    @property
    def trained_model_file_path(self) -> str:
        return os.path.join(self.model_trainer_dir, C.MODEL_TRAINER_TRAINED_MODEL_DIR, C.MODEL_TRAINER_TRAINED_MODEL_FILE_NAME)

    expected_accuracy: float = C.MODEL_TRAINER_EXPECTED_SCORE
    overfit_underfit_threshold: float = C.MODEL_TRAINER_OVERFIT_UNDERFIT_THRESHOLD

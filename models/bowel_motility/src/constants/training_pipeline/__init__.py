"""Pipeline constants — paths, hyperparameters, schema location.

Override per-pipeline as needed by editing this file. The entity dataclasses
read from these constants at runtime, so any change here propagates without
touching the components.
"""
from __future__ import annotations

import os

# ── Pipeline metadata ───────────────────────────────────────────────────
PIPELINE_NAME: str = "bowel_motility"
ARTIFACT_DIR: str = "artifacts"
SAVED_MODEL_DIR: str = "saved_models"

# ── Data ingestion ──────────────────────────────────────────────────────
DATA_INGESTION_DIR_NAME: str = "data_ingestion"
DATA_INGESTION_FEATURE_STORE_DIR: str = "feature_store"
DATA_INGESTION_INGESTED_DIR: str = "ingested"
DATA_INGESTION_TRAIN_TEST_SPLIT_RATIO: float = 0.2
DATA_INGESTION_RAW_FILE_NAME: str = "raw.csv"
DATA_INGESTION_TRAIN_FILE_NAME: str = "train.csv"
DATA_INGESTION_TEST_FILE_NAME: str = "test.csv"

# ── Data validation ─────────────────────────────────────────────────────
DATA_VALIDATION_DIR_NAME: str = "data_validation"
DATA_VALIDATION_VALID_DIR: str = "validated"
DATA_VALIDATION_INVALID_DIR: str = "invalid"
DATA_VALIDATION_DRIFT_REPORT_FILE_NAME: str = "drift_report.yaml"
SCHEMA_FILE_PATH: str = os.path.join("data_schema", "schema.yaml")

# ── Data transformation ─────────────────────────────────────────────────
DATA_TRANSFORMATION_DIR_NAME: str = "data_transformation"
DATA_TRANSFORMATION_TRANSFORMED_DIR: str = "transformed"
DATA_TRANSFORMATION_OBJECT_DIR: str = "transformed_object"
PREPROCESSING_OBJECT_FILE_NAME: str = "preprocessing.pkl"

# ── Model trainer ───────────────────────────────────────────────────────
MODEL_TRAINER_DIR_NAME: str = "model_trainer"
MODEL_TRAINER_TRAINED_MODEL_DIR: str = "trained_model"
MODEL_TRAINER_TRAINED_MODEL_FILE_NAME: str = "model.pkl"
MODEL_TRAINER_EXPECTED_SCORE: float = 0.6
MODEL_TRAINER_OVERFIT_UNDERFIT_THRESHOLD: float = 0.05

"""End-to-end training trigger for this pipeline.

Run from the pipeline root:

    cd models/<pipeline_slug>
    python main.py

This walks the four components in sequence — DataIngestion -> DataValidation
-> DataTransformation -> ModelTrainer — wrapping every stage in the
MedVerseException so failures surface with the file + line that caused them.

Equivalent to `python -m src.pipeline.training_pipeline`, but keeps the
explicit step-by-step logging that's useful when you're filling in stubs.
"""
from __future__ import annotations

import os
import sys

# Make the repo-root pipeline_utils.py importable while running from this
# pipeline's directory. (cwd-then-repo-root keeps the local `src` package
# winning the namespace race.)
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.append(_REPO_ROOT)

# Load .env (Groq keys, KAGGLE_*, HF_TOKEN, MEDVERSE_FETCH_LARGE) before
# any component imports try to read them.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_REPO_ROOT, ".env"))
except ImportError:
    pass

from src.components.data_ingestion import DataIngestion
from src.components.data_validation import DataValidation
from src.components.data_transformation import DataTransformation
from src.components.model_trainer import ModelTrainer
from src.entity.config_entity import (
    TrainingPipelineConfig,
    DataIngestionConfig,
    DataValidationConfig,
    DataTransformationConfig,
    ModelTrainerConfig,
)
from src.exception.exception import MedVerseException
from src.logging.logger import logging


if __name__ == "__main__":
    try:
        training_pipeline_config = TrainingPipelineConfig()

        data_ingestion_config = DataIngestionConfig(training_pipeline_config)
        data_ingestion = DataIngestion(data_ingestion_config)
        logging.info("Initiate the data ingestion")
        data_ingestion_artifact = data_ingestion.initiate_data_ingestion()
        logging.info("Data ingestion completed")
        print(data_ingestion_artifact)

        data_validation_config = DataValidationConfig(training_pipeline_config)
        data_validation = DataValidation(data_ingestion_artifact, data_validation_config)
        logging.info("Initiate the data validation")
        data_validation_artifact = data_validation.initiate_data_validation()
        logging.info("Data validation completed")
        print(data_validation_artifact)

        data_transformation_config = DataTransformationConfig(training_pipeline_config)
        logging.info("Data transformation started")
        data_transformation = DataTransformation(data_validation_artifact, data_transformation_config)
        data_transformation_artifact = data_transformation.initiate_data_transformation()
        print(data_transformation_artifact)
        logging.info("Data transformation completed")

        logging.info("Model training started")
        model_trainer_config = ModelTrainerConfig(training_pipeline_config)
        model_trainer = ModelTrainer(
            transformation_artifact=data_transformation_artifact,
            config=model_trainer_config,
        )
        model_trainer_artifact = model_trainer.initiate_model_trainer()
        print(model_trainer_artifact)
        logging.info("Model training artifact created")

    except Exception as e:
        raise MedVerseException(e, sys) from e

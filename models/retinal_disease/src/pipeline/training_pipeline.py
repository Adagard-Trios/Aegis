"""End-to-end training pipeline orchestrator.

Run as a module from the pipeline root:

    python -m src.pipeline.training_pipeline

It walks DataIngestion -> DataValidation -> DataTransformation -> ModelTrainer
and returns the final ModelTrainerArtifact.
"""
from __future__ import annotations

import sys
from typing import Optional

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
from src.entity.artifact_entity import ModelTrainerArtifact
from src.exception.exception import MedVerseException
from src.logging.logger import logging


class TrainingPipeline:
    def __init__(self, pipeline_config: Optional[TrainingPipelineConfig] = None):
        self.pipeline_config = pipeline_config or TrainingPipelineConfig()

    def start(
        self,
        ingestion_cls=DataIngestion,
        validation_cls=DataValidation,
        transformation_cls=DataTransformation,
        trainer_cls=ModelTrainer,
    ) -> ModelTrainerArtifact:
        try:
            logging.info("TrainingPipeline: ingestion")
            ingestion_cfg = DataIngestionConfig(self.pipeline_config)
            ingestion_artifact = ingestion_cls(ingestion_cfg).initiate_data_ingestion()

            logging.info("TrainingPipeline: validation")
            validation_cfg = DataValidationConfig(self.pipeline_config)
            validation_artifact = validation_cls(ingestion_artifact, validation_cfg).initiate_data_validation()

            logging.info("TrainingPipeline: transformation")
            transformation_cfg = DataTransformationConfig(self.pipeline_config)
            transformation_artifact = transformation_cls(
                validation_artifact, transformation_cfg
            ).initiate_data_transformation()

            logging.info("TrainingPipeline: training")
            trainer_cfg = ModelTrainerConfig(self.pipeline_config)
            trainer_artifact = trainer_cls(transformation_artifact, trainer_cfg).initiate_model_trainer()

            logging.info(f"TrainingPipeline: done -> {trainer_artifact.trained_model_file_path}")
            return trainer_artifact
        except Exception as e:
            raise MedVerseException(e, sys) from e


if __name__ == "__main__":  # pragma: no cover
    TrainingPipeline().start()

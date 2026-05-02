"""Data ingestion stage — pull source data + train/test split.

Fill in `_load_dataframe` for your data source (S3, Kaggle, local CSV,
hospital DB, …). Everything else is generic.
"""
from __future__ import annotations

import os
import sys
from typing import Tuple

import pandas as pd
from sklearn.model_selection import train_test_split

from src.entity.config_entity import DataIngestionConfig
from src.entity.artifact_entity import DataIngestionArtifact
from src.exception.exception import MedVerseException
from src.logging.logger import logging


class DataIngestion:
    def __init__(self, config: DataIngestionConfig):
        self.config = config

    def _load_dataframe(self) -> pd.DataFrame:
        """Subclass / replace this for the concrete data source.

        Override this in the per-pipeline implementation. The base
        implementation raises so an unconfigured pipeline fails clearly.
        """
        raise NotImplementedError(
            "DataIngestion._load_dataframe is a stub. Override it to return the "
            "raw DataFrame for this pipeline."
        )

    def _persist_feature_store(self, df: pd.DataFrame) -> None:
        os.makedirs(os.path.dirname(self.config.feature_store_file_path), exist_ok=True)
        df.to_csv(self.config.feature_store_file_path, index=False)

    def _split_and_persist(self, df: pd.DataFrame) -> Tuple[str, str]:
        train_df, test_df = train_test_split(
            df, test_size=self.config.train_test_split_ratio, random_state=42
        )
        os.makedirs(os.path.dirname(self.config.training_file_path), exist_ok=True)
        train_df.to_csv(self.config.training_file_path, index=False)
        test_df.to_csv(self.config.testing_file_path, index=False)
        return self.config.training_file_path, self.config.testing_file_path

    def initiate_data_ingestion(self) -> DataIngestionArtifact:
        try:
            logging.info("DataIngestion: loading source dataframe")
            df = self._load_dataframe()
            self._persist_feature_store(df)
            train_path, test_path = self._split_and_persist(df)
            logging.info(f"DataIngestion: train={train_path} test={test_path}")
            return DataIngestionArtifact(trained_file_path=train_path, test_file_path=test_path)
        except Exception as e:
            raise MedVerseException(e, sys) from e

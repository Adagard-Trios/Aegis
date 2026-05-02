"""bowel_motility — DataIngestion

Source: synthetic generator (no real public dataset is shipped — the
source notebook itself only has a generator). The synthetic schema
mirrors a colonic-manometry pressure series with 4 channels.
"""
from __future__ import annotations

import os
import sys
from typing import Tuple

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.append(_REPO_ROOT)

import pandas as pd
from sklearn.model_selection import train_test_split

import pipeline_utils as dl  # noqa: E402

from src.entity.config_entity import DataIngestionConfig
from src.entity.artifact_entity import DataIngestionArtifact
from src.exception.exception import MedVerseException
from src.logging.logger import logging


import numpy as np


class DataIngestion:
    def __init__(self, config: DataIngestionConfig):
        self.config = config

    def _load_dataframe(self) -> pd.DataFrame:
        # Deterministic, small synthetic dataset. Replace with a real source by
        # overriding this method when a clinical dataset is integrated.
        rng = np.random.default_rng(seed=42)
        n = 2000
        data = {
            f"ch{ch}_{stat}": rng.normal(loc=0.0 if stat == "mean" else 1.0, scale=0.3, size=n)
            for ch in range(4)
            for stat in ("mean", "std", "p95")
        }
        labels = rng.choice([0, 1, 2], size=n, p=[0.55, 0.30, 0.15])  # quiet / normal / hyperactive
        df = pd.DataFrame(data)
        df["target"] = labels
        logging.info(f"bowel_motility: synthetic {len(df)} rows × {df.shape[1]} cols")
        return df

    def _persist_feature_store(self, df: pd.DataFrame) -> None:
        os.makedirs(os.path.dirname(self.config.feature_store_file_path), exist_ok=True)
        df.to_csv(self.config.feature_store_file_path, index=False)

    def _split_and_persist(self, df: pd.DataFrame) -> Tuple[str, str]:
        try:
            train_df, test_df = train_test_split(
                df, test_size=self.config.train_test_split_ratio, random_state=42,
                stratify=df["target"] if "target" in df.columns else None,
            )
        except ValueError:
            train_df, test_df = train_test_split(
                df, test_size=self.config.train_test_split_ratio, random_state=42
            )
        os.makedirs(os.path.dirname(self.config.training_file_path), exist_ok=True)
        train_df.to_csv(self.config.training_file_path, index=False)
        test_df.to_csv(self.config.testing_file_path, index=False)
        return self.config.training_file_path, self.config.testing_file_path

    def initiate_data_ingestion(self) -> DataIngestionArtifact:
        try:
            df = self._load_dataframe()
            self._persist_feature_store(df)
            train_path, test_path = self._split_and_persist(df)
            return DataIngestionArtifact(trained_file_path=train_path, test_file_path=test_path)
        except Exception as e:
            raise MedVerseException(e, sys) from e

"""stress_ans — DataIngestion

Source: WESAD requires email registration at uni-siegen.de — not auto-fetched.
Default behaviour: synthetic generator (matches the source notebook).
When you have WESAD locally, point WESAD_ROOT at the extracted directory.
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
        if os.environ.get("WESAD_ROOT"):
            # User has the real dataset — leave a clear hook for downstream work.
            raise dl.DatasetUnavailable(
                "WESAD real-data ingestion not yet implemented",
                hint=(
                    "WESAD_ROOT is set, but the real WESAD parser is a follow-up "
                    "(per-subject .pkl reader). Unset WESAD_ROOT to use the "
                    "synthetic generator, or implement the parser in this method."
                ),
            )
        rng = np.random.default_rng(seed=7)
        n = 3000
        df = pd.DataFrame({
            "hr_mean":    rng.normal(78, 12, n),
            "hr_std":     rng.normal(5, 1.5, n),
            "hrv_rmssd":  rng.normal(35, 12, n),
            "br_mean":    rng.normal(16, 3, n),
            "eda_mean":   rng.normal(2.0, 0.6, n),
            "eda_peaks":  rng.poisson(2.0, n).astype(float),
            "temp_mean":  rng.normal(33.5, 0.5, n),
        })
        # Stress label correlates with HR + EDA peaks (synthetic)
        score = 0.05 * df["hr_mean"] + 0.5 * df["eda_peaks"] - 0.04 * df["hrv_rmssd"]
        thr_low, thr_high = np.percentile(score, [40, 80])
        labels = np.where(score < thr_low, 0, np.where(score < thr_high, 1, 2))  # baseline / stress / amusement
        df["target"] = labels
        logging.info(f"stress_ans: synthetic {len(df)} rows")
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

"""cardiac_age — DataIngestion

Source: PTB-XL (PhysioNet, 25 GB) — patient age regression target.
Gated by MEDVERSE_FETCH_LARGE=true.
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


PHYSIONET_URL = "https://physionet.org/files/ptb-xl/1.0.3/"


class DataIngestion:
    def __init__(self, config: DataIngestionConfig):
        self.config = config

    def _load_dataframe(self) -> pd.DataFrame:
        target = dl.cache_dir("cardiac_age", "ptbxl")
        if not dl.is_dir_nonempty(target):
            dl.require_large(reason="PTB-XL is 25 GB.", dataset_name="PTB-XL", size="25 GB")
            logging.info("cardiac_age: downloading PTB-XL from PhysioNet")
            dl.download_physionet(PHYSIONET_URL, target)
        meta = next(target.rglob("ptbxl_database.csv"), None)
        if meta is None:
            raise dl.DatasetUnavailable(
                "cardiac_age: ptbxl_database.csv not found",
                hint=f"Inspect {target}; redo with MEDVERSE_FETCH_LARGE=true to retry.",
            )
        df = pd.read_csv(meta)
        df["age"] = pd.to_numeric(df.get("age", 0), errors="coerce")
        df = df.dropna(subset=["age"]).reset_index(drop=True)
        df["sex"] = pd.to_numeric(df.get("sex", 0), errors="coerce").fillna(0).astype(int)
        df["heart_axis_left"] = (df.get("heart_axis", "").astype(str) == "LAD").astype(int)
        df["heart_axis_right"] = (df.get("heart_axis", "").astype(str) == "RAD").astype(int)
        df = df.rename(columns={"age": "target"})
        out = df[["sex", "heart_axis_left", "heart_axis_right", "target"]]
        logging.info(f"cardiac_age: {len(out)} records, age range {out['target'].min():.0f}-{out['target'].max():.0f}")
        return out

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

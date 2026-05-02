"""fetal_health — DataIngestion

Source: UCI Cardiotocography (CTG.xls — 2126 records, 22 features). No auth.
Optional: CTU-UHB CTG waveforms (PhysioNet) when MEDVERSE_FETCH_LARGE=true.
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


UCI_CTG_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00193/CTG.xls"
PHYSIONET_CTU_URL = "https://physionet.org/files/ctu-uhb-ctgdb/1.0.0/"


class DataIngestion:
    def __init__(self, config: DataIngestionConfig):
        self.config = config

    def _load_dataframe(self) -> pd.DataFrame:
        ctg_xls = dl.cache_dir("fetal_health", "uci") / "CTG.xls"
        if not ctg_xls.exists() or ctg_xls.stat().st_size == 0:
            logging.info("fetal_health: downloading UCI CTG.xls")
            dl.download_file(UCI_CTG_URL, ctg_xls)
        # The UCI CTG file uses sheet name "Raw Data"; header row is 1.
        dl.require_module("openpyxl", "pip install openpyxl>=3.1")
        df = pd.read_excel(ctg_xls, sheet_name="Raw Data", header=1)
        # Drop rows where the target is NaN (footer rows in the original sheet)
        if "NSP" not in df.columns:
            raise dl.DatasetUnavailable(
                "UCI CTG.xls missing 'NSP' column",
                hint="Delete models/fetal_health/data/uci/CTG.xls and re-run python main.py",
            )
        df = df.dropna(subset=["NSP"]).reset_index(drop=True)
        df = df.rename(columns={"NSP": "target"})
        df["target"] = df["target"].astype(int)

        # Optional CTU waveform download — gated
        if dl.is_large_allowed():
            ctu_dir = dl.cache_dir("fetal_health", "ctu_uhb")
            if not dl.is_dir_nonempty(ctu_dir):
                logging.info("fetal_health: MEDVERSE_FETCH_LARGE=true → downloading CTU-UHB")
                try:
                    dl.download_physionet(PHYSIONET_CTU_URL, ctu_dir)
                except Exception as e:
                    logging.warning(f"fetal_health: CTU-UHB skipped ({e})")

        # Drop columns that aren't useful features
        drop_cols = [c for c in ("FileName", "Date", "SegFile", "b", "e") if c in df.columns]
        df = df.drop(columns=drop_cols)
        # Keep only numeric features
        df = df.select_dtypes(include="number")
        logging.info(f"fetal_health: {len(df)} rows × {df.shape[1]} cols")
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

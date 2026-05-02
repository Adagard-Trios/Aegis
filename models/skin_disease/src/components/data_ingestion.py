"""skin_disease — DataIngestion

Source: HAM10000 (Kaggle) — 10K dermoscopic images + metadata.
Returns a metadata DataFrame with image_path + dx label so the
downstream image transform can read the files lazily.
Optional: ISIC 2024 challenge data behind MEDVERSE_FETCH_LARGE=true.
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


KAGGLE_HAM_SLUG = "kmader/skin-cancer-mnist-ham10000"
KAGGLE_ISIC_2024_COMPETITION = "isic-2024-challenge"


class DataIngestion:
    def __init__(self, config: DataIngestionConfig):
        self.config = config

    def _load_dataframe(self) -> pd.DataFrame:
        target = dl.cache_dir("skin_disease", "ham10000")
        if not dl.is_dir_nonempty(target):
            dl.require_env(
                "KAGGLE_USERNAME", "KAGGLE_KEY",
                hint="Set KAGGLE_USERNAME and KAGGLE_KEY (https://www.kaggle.com/settings/account) in .env",
            )
            dl.download_kaggle_dataset(KAGGLE_HAM_SLUG, target)

        # HAM10000 ships HAM10000_metadata.csv with image_id + dx
        meta_csv = next(target.rglob("HAM10000_metadata.csv"), None)
        if meta_csv is None:
            raise dl.DatasetUnavailable(
                "HAM10000 metadata csv not found in extracted bundle",
                hint=f"Inspect {target}; delete and re-download to retry.",
            )
        meta = pd.read_csv(meta_csv)
        # Build absolute image_path columns by scanning the two image dirs Kaggle ships
        image_paths = {p.stem: str(p) for p in target.rglob("*.jpg")}
        meta["image_path"] = meta["image_id"].map(image_paths)
        meta = meta.dropna(subset=["image_path", "dx"]).reset_index(drop=True)
        meta = meta.rename(columns={"dx": "target"})
        # Keep a small numeric-only fingerprint for the default tabular trainer.
        df = meta[["target", "image_path", "age"]].copy()
        df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(df["age"].median()).astype(float) if "age" in df else 0.0
        if dl.is_large_allowed():
            isic_dir = dl.cache_dir("skin_disease", "isic2024")
            if not dl.is_dir_nonempty(isic_dir):
                logging.info("skin_disease: MEDVERSE_FETCH_LARGE=true → downloading ISIC 2024")
                try:
                    dl.download_kaggle_competition(KAGGLE_ISIC_2024_COMPETITION, isic_dir)
                except Exception as e:
                    logging.warning(f"skin_disease: ISIC 2024 skipped ({e})")
        logging.info(f"skin_disease: {len(df)} HAM10000 rows; classes {sorted(df['target'].unique())}")
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

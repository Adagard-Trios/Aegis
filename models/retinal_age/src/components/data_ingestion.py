"""retinal_age — DataIngestion

Source: ODIR-5K (Kaggle) for fundus images; RETFound MAE weights
(rmaphoh/RETFound_MAE on HuggingFace) for the encoder backbone.
Target is the patient age (regression).
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


KAGGLE_ODIR_SLUG = "jeftaadriel/oia-odir-dataset"
RETFOUND_REPO = "rmaphoh/RETFound_MAE"
RETFOUND_FILE = "RETFound_mae_natureCFP.pth"


class DataIngestion:
    def __init__(self, config: DataIngestionConfig):
        self.config = config

    def _load_dataframe(self) -> pd.DataFrame:
        target = dl.cache_dir("retinal_age", "odir")
        if not dl.is_dir_nonempty(target):
            dl.require_env("KAGGLE_USERNAME", "KAGGLE_KEY", hint="Add Kaggle creds to .env")
            dl.download_kaggle_dataset(KAGGLE_ODIR_SLUG, target)
        # RETFound weights cached for the model trainer to load
        weights_dir = dl.cache_dir("retinal_age", "retfound")
        weights_path = weights_dir / RETFOUND_FILE
        if not weights_path.exists():
            try:
                dl.download_huggingface_file(RETFOUND_REPO, RETFOUND_FILE, weights_path)
            except dl.DatasetUnavailable as e:
                logging.warning(f"retinal_age: RETFound weights skipped ({e}). Pipeline will train on tabular features only.")

        meta_path = next(target.rglob("*Annotation*.xlsx"), None) or next(target.rglob("*.csv"), None)
        if meta_path is None:
            raise dl.DatasetUnavailable(
                "retinal_age: annotation not found in ODIR cache",
                hint=f"Inspect {target}",
            )
        if str(meta_path).endswith(".xlsx"):
            dl.require_module("openpyxl", "pip install openpyxl")
            meta = pd.read_excel(meta_path)
        else:
            meta = pd.read_csv(meta_path)
        df = meta.copy()
        df["age"] = pd.to_numeric(df.get("Patient Age", df.get("age")), errors="coerce")
        df = df.dropna(subset=["age"]).reset_index(drop=True)
        df = df.rename(columns={"age": "target"})
        # Image paths for downstream image trainers
        image_paths = {p.stem: str(p) for p in target.rglob("*.jpg")}
        if "Left-Fundus" in df.columns:
            df["image_path"] = df["Left-Fundus"].astype(str).str.replace(".jpg", "", regex=False).map(image_paths)
        # Sex column → numeric
        if "Patient Sex" in df.columns:
            df["sex"] = (df["Patient Sex"].astype(str).str.strip().str.upper() == "F").astype(int)
        else:
            df["sex"] = 0
        out = df[["target", "sex", "image_path"]].copy() if "image_path" in df else df[["target", "sex"]].copy()
        logging.info(f"retinal_age: {len(out)} rows")
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

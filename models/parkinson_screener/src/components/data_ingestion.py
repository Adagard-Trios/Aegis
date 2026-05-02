"""parkinson_screener — DataIngestion

Source (default, no auth): UCI Parkinsons voice dataset.
URL: https://archive.ics.uci.edu/ml/machine-learning-databases/parkinsons/parkinsons.data

Optional: WearGait-PD wearable-motion dataset on Synapse (syn52540892) when
SYNAPSE_AUTH_TOKEN is set. Falls back to voice-only when token is missing —
the resulting model still trains, just without gait features.
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


UCI_VOICE_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/parkinsons/parkinsons.data"
)
SYNAPSE_GAIT_ENTITY = "syn52540892"  # WearGait-PD


class DataIngestion:
    def __init__(self, config: DataIngestionConfig):
        self.config = config

    def _load_dataframe(self) -> pd.DataFrame:
        voice_csv = dl.cache_dir("parkinson_screener", "voice") / "parkinsons.data"
        if not voice_csv.exists() or voice_csv.stat().st_size == 0:
            logging.info("parkinson_screener: downloading UCI parkinsons voice CSV")
            dl.download_file(UCI_VOICE_URL, voice_csv)
        df = pd.read_csv(voice_csv)
        df = df.drop(columns=["name"], errors="ignore")
        if "status" not in df.columns:
            raise dl.DatasetUnavailable(
                "UCI parkinsons CSV missing 'status' column",
                hint="Cached file at models/parkinson_screener/data/voice/parkinsons.data may be corrupt; delete and re-run.",
            )
        df = df.rename(columns={"status": "target"})

        # Optional WearGait-PD download (Synapse) — token-gated
        if os.environ.get("SYNAPSE_AUTH_TOKEN"):
            try:
                gait_dir = dl.cache_dir("parkinson_screener", "weargait")
                dl.download_synapse_entity(SYNAPSE_GAIT_ENTITY, gait_dir)
                logging.info(f"parkinson_screener: WearGait-PD cached at {gait_dir}")
            except Exception as e:
                logging.warning(f"parkinson_screener: WearGait-PD skipped ({e})")

        logging.info(f"parkinson_screener: {len(df)} rows × {df.shape[1]} cols")
        return df

    def _persist_feature_store(self, df: pd.DataFrame) -> None:
        os.makedirs(os.path.dirname(self.config.feature_store_file_path), exist_ok=True)
        df.to_csv(self.config.feature_store_file_path, index=False)

    def _split_and_persist(self, df: pd.DataFrame) -> Tuple[str, str]:
        train_df, test_df = train_test_split(
            df, test_size=self.config.train_test_split_ratio, random_state=42, stratify=df["target"]
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

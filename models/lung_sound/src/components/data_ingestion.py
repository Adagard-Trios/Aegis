"""lung_sound — DataIngestion

Source: ICBHI 2017 respiratory sound database (~920 wav cycles).
Tries Kaggle (`vbookshelf/respiratory-sound-database`) first when KAGGLE_*
creds are present, otherwise falls back to the direct ZIP mirror.
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


DIRECT_URL = "https://bhichallenge.med.auth.gr/sites/default/files/ICBHI_final_database/ICBHI_final_database.zip"
KAGGLE_SLUG = "vbookshelf/respiratory-sound-database"


def _cycle_features(wav_path):
    import numpy as np
    sf = dl.require_module("soundfile", "pip install soundfile")  # bundled with librosa wheels
    audio, fs = sf.read(str(wav_path))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return {
        "duration_s": float(len(audio) / fs),
        "rms": float(np.sqrt(np.mean(audio ** 2))),
        "zcr": float(np.mean(np.abs(np.diff(np.sign(audio))))),
        "p95": float(np.percentile(np.abs(audio), 95)),
        "p05": float(np.percentile(np.abs(audio), 5)),
    }


class DataIngestion:
    def __init__(self, config: DataIngestionConfig):
        self.config = config

    def _load_dataframe(self) -> pd.DataFrame:
        target = dl.cache_dir("lung_sound", "icbhi")
        if not dl.is_dir_nonempty(target):
            if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
                logging.info("lung_sound: downloading from Kaggle")
                try:
                    dl.download_kaggle_dataset(KAGGLE_SLUG, target)
                except Exception as e:
                    logging.warning(f"lung_sound: Kaggle failed ({e}); trying direct mirror")
                    dl.download_file(DIRECT_URL, target / "icbhi.zip")
                    dl.unzip(target / "icbhi.zip", target)
            else:
                logging.info("lung_sound: downloading direct ZIP (no Kaggle creds)")
                dl.download_file(DIRECT_URL, target / "icbhi.zip")
                dl.unzip(target / "icbhi.zip", target)

        # Find every wav, extract features, label by parent diagnosis if available
        rows = []
        diag_csv = next(target.rglob("patient_diagnosis.csv"), None)
        diag_map = {}
        if diag_csv is not None:
            try:
                diag_df = pd.read_csv(diag_csv, header=None, names=["pid", "diagnosis"])
                diag_map = dict(zip(diag_df["pid"].astype(str), diag_df["diagnosis"]))
            except Exception:
                pass
        for wav in target.rglob("*.wav"):
            try:
                feats = _cycle_features(wav)
            except Exception as e:
                logging.warning(f"lung_sound: skip {wav.name} ({e})")
                continue
            pid = wav.stem.split("_")[0]
            feats["target"] = str(diag_map.get(pid, "Unknown"))
            rows.append(feats)
            if len(rows) >= 1500:  # cap for fast iteration
                break
        if not rows:
            raise dl.DatasetUnavailable(
                "lung_sound: ICBHI extraction produced no .wav files",
                hint=f"Inspect {target}; the ZIP may be incomplete. Delete and re-run.",
            )
        df = pd.DataFrame(rows)
        logging.info(f"lung_sound: {len(df)} rows, classes {sorted(df['target'].unique())}")
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

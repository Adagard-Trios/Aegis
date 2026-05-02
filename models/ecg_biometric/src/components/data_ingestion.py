"""ecg_biometric — DataIngestion

Source: PhysioNet ECG-ID database (90 subjects, 20-second ECG recordings).
URL: https://physionet.org/files/ecgiddb/1.0.0/  (~100 MB, no auth)

Each WFDB record is summarised into a small per-recording feature vector
(HR, ECG signal stats) labelled with the subject id (Person_XX). Downstream
the Siamese / classifier model treats subject_id as the target.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Tuple

# Make repo-root pipeline_utils.py importable when running from this pipeline.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.append(_REPO_ROOT)

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

import pipeline_utils as dl  # noqa: E402

from src.entity.config_entity import DataIngestionConfig
from src.entity.artifact_entity import DataIngestionArtifact
from src.exception.exception import MedVerseException
from src.logging.logger import logging


PHYSIONET_URL = "https://physionet.org/files/ecgiddb/1.0.0/"


def _record_features(record_dir: Path, record_name: str) -> dict:
    """Compute lightweight features for one ECG-ID record."""
    wfdb = dl.require_module("wfdb", "pip install wfdb>=4.1")
    rec = wfdb.rdrecord(str(record_dir / record_name))
    sig = rec.p_signal[:, 0]  # lead I — filtered
    fs = rec.fs
    # Simple beat detection via threshold over the derivative (good enough for stats)
    diff = np.diff(sig)
    peaks = np.where((diff[:-1] > np.percentile(diff, 95)) & (diff[1:] < 0))[0]
    if len(peaks) > 1:
        rr = np.diff(peaks) / fs
        hr = float(60.0 / rr.mean()) if rr.mean() > 0 else 0.0
        rr_std = float(np.std(rr))
    else:
        hr, rr_std = 0.0, 0.0
    return {
        "hr": hr,
        "rr_std": rr_std,
        "sig_mean": float(np.mean(sig)),
        "sig_std": float(np.std(sig)),
        "sig_p95": float(np.percentile(sig, 95)),
        "sig_p05": float(np.percentile(sig, 5)),
        "duration_s": float(len(sig) / fs),
    }


class DataIngestion:
    def __init__(self, config: DataIngestionConfig):
        self.config = config

    def _load_dataframe(self) -> pd.DataFrame:
        target = dl.cache_dir("ecg_biometric", "ecgid")
        # ECG-ID has 90 subjects (Person_01 ... Person_90). A partial cache
        # would silently train on a tiny subset and look broken. Re-download
        # if we don't have at least 70 subject dirs (some flexibility for
        # the rare PhysioNet hiccup).
        existing_persons = list(target.glob("Person_*"))
        if len(existing_persons) < 70:
            logging.info(
                f"ecg_biometric: cache has {len(existing_persons)}/90 subjects — downloading ECG-ID from PhysioNet"
            )
            dl.download_physionet(PHYSIONET_URL, target)
        # ECG-ID layout: <root>/Person_XX/rec_Y(.dat,.hea,.atr)
        rows = []
        for person_dir in sorted(target.glob("Person_*")):
            subject_id = person_dir.name  # 'Person_01' .. 'Person_90'
            # Each record is identified by <basename> shared by .dat/.hea
            for hea in sorted(person_dir.glob("*.hea")):
                rec_name = hea.stem
                try:
                    feats = _record_features(person_dir, rec_name)
                except Exception as e:
                    logging.warning(f"ecg_biometric: skip {person_dir.name}/{rec_name} ({e})")
                    continue
                feats["target"] = subject_id
                rows.append(feats)
        if not rows:
            raise dl.DatasetUnavailable(
                "ECG-ID download produced no usable records",
                hint=f"Inspect {target} for missing .dat/.hea files; re-run python main.py to retry.",
            )
        df = pd.DataFrame(rows)
        logging.info(f"ecg_biometric: built {len(df)} rows over {df['target'].nunique()} subjects")
        return df

    def _persist_feature_store(self, df: pd.DataFrame) -> None:
        os.makedirs(os.path.dirname(self.config.feature_store_file_path), exist_ok=True)
        df.to_csv(self.config.feature_store_file_path, index=False)

    def _split_and_persist(self, df: pd.DataFrame) -> Tuple[str, str]:
        # Stratify by subject so every split sees every class.
        try:
            train_df, test_df = train_test_split(
                df, test_size=self.config.train_test_split_ratio, random_state=42, stratify=df["target"]
            )
        except ValueError:
            # Some subjects have only 1 record — fall back to unstratified
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

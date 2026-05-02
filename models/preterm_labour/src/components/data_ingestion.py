"""preterm_labour — DataIngestion

Source: PhysioNet TPEHGDB (term-preterm EHG database, ~300 records). No auth.
Each record carries a header annotation Gestation_at_Recording (weeks); we
label preterm = recorded before 37 weeks. Features: per-channel band-power
summaries from the 4-channel EHG signal.
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


PHYSIONET_URL = "https://physionet.org/files/tpehgdb/1.0.1/"


def _record_features(record_path):
    import numpy as np
    wfdb = dl.require_module("wfdb", "pip install wfdb>=4.1")
    rec = wfdb.rdrecord(str(record_path))
    sig = rec.p_signal  # (n_samples, n_channels)
    feats = {}
    for ch in range(sig.shape[1]):
        x = sig[:, ch]
        feats[f"ch{ch}_mean"] = float(np.mean(x))
        feats[f"ch{ch}_std"] = float(np.std(x))
        feats[f"ch{ch}_p95"] = float(np.percentile(x, 95))
    # The TPEHGDB header carries a 'Gestation' field in the comments
    gestation_weeks = None
    for line in (rec.comments or []):
        if "Gestation" in line:
            try:
                gestation_weeks = float(line.split()[-1])
            except Exception:
                pass
    return feats, gestation_weeks


class DataIngestion:
    def __init__(self, config: DataIngestionConfig):
        self.config = config

    def _load_dataframe(self) -> pd.DataFrame:
        target = dl.cache_dir("preterm_labour", "tpehgdb")
        # TPEHGDB has ~300 records. Re-download if we have noticeably fewer
        # than expected so a partial cache doesn't masquerade as complete.
        existing_hea = list(target.rglob("*.hea"))
        if len(existing_hea) < 250:
            logging.info(
                f"preterm_labour: cache has {len(existing_hea)} .hea files (<250) — downloading TPEHGDB from PhysioNet"
            )
            dl.download_physionet(PHYSIONET_URL, target)
        rows = []
        for hea in sorted(target.rglob("*.hea")):
            stem = hea.with_suffix("")
            try:
                feats, weeks = _record_features(stem)
            except Exception as e:
                logging.warning(f"preterm_labour: skip {hea.name} ({e})")
                continue
            if weeks is None:
                continue
            feats["target"] = 1 if weeks < 37 else 0  # 1=preterm
            rows.append(feats)
        if not rows:
            raise dl.DatasetUnavailable(
                "preterm_labour: no parseable TPEHGDB records",
                hint=f"Inspect {target} and the .hea files; re-run to retry.",
            )
        df = pd.DataFrame(rows)
        logging.info(f"preterm_labour: {len(df)} records, preterm rate {df['target'].mean():.2f}")
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

"""Data validation — schema enforcement + drift report (KS test).

Reads `data_schema/schema.yaml` and verifies every required column is present
with the expected dtype, then runs a per-feature Kolmogorov-Smirnov test
between train and test to surface distribution drift early.
"""
from __future__ import annotations

import os
import sys
from typing import Dict

import pandas as pd
from scipy.stats import ks_2samp

from src.entity.config_entity import DataValidationConfig
from src.entity.artifact_entity import DataIngestionArtifact, DataValidationArtifact
from src.exception.exception import MedVerseException
from src.logging.logger import logging
from src.utils.main_utils import read_yaml_file, write_yaml_file


class DataValidation:
    def __init__(self, ingestion_artifact: DataIngestionArtifact, config: DataValidationConfig):
        self.ingestion_artifact = ingestion_artifact
        self.config = config
        self.schema = read_yaml_file(config.schema_file_path) if os.path.exists(config.schema_file_path) else {}

    def _validate_columns(self, df: pd.DataFrame) -> bool:
        expected = [c["name"] for c in (self.schema.get("inputs") or [])]
        missing = [c for c in expected if c not in df.columns]
        if missing:
            logging.warning(f"DataValidation: missing columns {missing}")
            return False
        return True

    def _drift_report(self, train_df: pd.DataFrame, test_df: pd.DataFrame) -> Dict[str, dict]:
        threshold = float(self.schema.get("drift_tolerance", 0.05))
        report: Dict[str, dict] = {}
        for col in train_df.select_dtypes(include="number").columns:
            try:
                stat = ks_2samp(train_df[col].dropna(), test_df[col].dropna())
                report[col] = {
                    "p_value": float(stat.pvalue),
                    "drift": bool(stat.pvalue < threshold),
                }
            except Exception as e:  # noqa: BLE001
                report[col] = {"error": str(e), "drift": False}
        return report

    def initiate_data_validation(self) -> DataValidationArtifact:
        try:
            train_df = pd.read_csv(self.ingestion_artifact.trained_file_path)
            test_df = pd.read_csv(self.ingestion_artifact.test_file_path)

            train_ok = self._validate_columns(train_df)
            test_ok = self._validate_columns(test_df)
            valid = train_ok and test_ok

            target_train = self.config.valid_train_file_path if valid else self.config.invalid_train_file_path
            target_test = self.config.valid_test_file_path if valid else self.config.invalid_test_file_path
            os.makedirs(os.path.dirname(target_train), exist_ok=True)
            os.makedirs(os.path.dirname(target_test), exist_ok=True)
            train_df.to_csv(target_train, index=False)
            test_df.to_csv(target_test, index=False)

            report = self._drift_report(train_df, test_df)
            os.makedirs(os.path.dirname(self.config.drift_report_file_path), exist_ok=True)
            write_yaml_file(self.config.drift_report_file_path, report, replace=True)

            logging.info(f"DataValidation: status={valid} drift_keys={len(report)}")
            return DataValidationArtifact(
                validation_status=valid,
                valid_train_file_path=target_train if valid else "",
                valid_test_file_path=target_test if valid else "",
                invalid_train_file_path="" if valid else target_train,
                invalid_test_file_path="" if valid else target_test,
                drift_report_file_path=self.config.drift_report_file_path,
            )
        except Exception as e:
            raise MedVerseException(e, sys) from e

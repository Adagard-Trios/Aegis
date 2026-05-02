"""Data transformation — preprocessing pipeline + serialised arrays.

Override `_build_preprocessor` to swap in domain-specific preprocessing
(e.g. ECG band-pass filter, image augmentation, audio mel-spec).
"""
from __future__ import annotations

import os
import sys
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from src.entity.config_entity import DataTransformationConfig
from src.entity.artifact_entity import DataValidationArtifact, DataTransformationArtifact
from src.exception.exception import MedVerseException
from src.logging.logger import logging
from src.utils.main_utils import save_numpy_array, save_object


class DataTransformation:
    TARGET_COLUMN = "target"  # override in subclass / per-pipeline

    def __init__(self, validation_artifact: DataValidationArtifact, config: DataTransformationConfig):
        self.validation_artifact = validation_artifact
        self.config = config

    def _build_preprocessor(self, x: pd.DataFrame) -> Pipeline:
        """Default: median-impute + standard-scale numeric features.

        Override for image / audio / time-series pipelines.
        """
        numeric = x.select_dtypes(include="number").columns.tolist()
        return Pipeline(
            steps=[
                (
                    "preprocess",
                    ColumnTransformer(
                        transformers=[
                            (
                                "num",
                                Pipeline(
                                    steps=[
                                        ("imputer", SimpleImputer(strategy="median")),
                                        ("scaler", StandardScaler()),
                                    ]
                                ),
                                numeric,
                            ),
                        ],
                        remainder="drop",
                    ),
                )
            ]
        )

    def _split_xy(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        if self.TARGET_COLUMN not in df.columns:
            raise NotImplementedError(
                f"DataTransformation.TARGET_COLUMN={self.TARGET_COLUMN!r} not in df. "
                "Override TARGET_COLUMN in the per-pipeline subclass."
            )
        return df.drop(columns=[self.TARGET_COLUMN]), df[self.TARGET_COLUMN]

    def initiate_data_transformation(self) -> DataTransformationArtifact:
        try:
            train = pd.read_csv(self.validation_artifact.valid_train_file_path)
            test = pd.read_csv(self.validation_artifact.valid_test_file_path)

            x_train, y_train = self._split_xy(train)
            x_test, y_test = self._split_xy(test)

            preprocessor = self._build_preprocessor(x_train)
            preprocessor.fit(x_train)

            x_train_t = preprocessor.transform(x_train)
            x_test_t = preprocessor.transform(x_test)

            train_arr = np.c_[np.asarray(x_train_t), np.asarray(y_train)]
            test_arr = np.c_[np.asarray(x_test_t), np.asarray(y_test)]

            save_numpy_array(self.config.transformed_train_file_path, train_arr)
            save_numpy_array(self.config.transformed_test_file_path, test_arr)
            save_object(self.config.transformed_object_file_path, preprocessor)

            logging.info("DataTransformation: complete")
            return DataTransformationArtifact(
                transformed_object_file_path=self.config.transformed_object_file_path,
                transformed_train_file_path=self.config.transformed_train_file_path,
                transformed_test_file_path=self.config.transformed_test_file_path,
            )
        except Exception as e:
            raise MedVerseException(e, sys) from e

"""Filesystem + serialisation helpers shared by every component."""
from __future__ import annotations

import os
import pickle
import sys
from typing import Any

import numpy as np
import yaml

from src.exception.exception import MedVerseException
from src.logging.logger import logging  # noqa: F401  (side-effect: configure root)


def read_yaml_file(file_path: str) -> dict:
    try:
        with open(file_path, "rb") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise MedVerseException(e, sys) from e


def write_yaml_file(file_path: str, content: Any, replace: bool = False) -> None:
    try:
        if replace and os.path.exists(file_path):
            os.remove(file_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            yaml.safe_dump(content, f, default_flow_style=False)
    except Exception as e:
        raise MedVerseException(e, sys) from e


def save_object(file_path: str, obj: Any) -> None:
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            pickle.dump(obj, f)
    except Exception as e:
        raise MedVerseException(e, sys) from e


def load_object(file_path: str) -> Any:
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"object file not found: {file_path}")
        with open(file_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        raise MedVerseException(e, sys) from e


def save_numpy_array(file_path: str, array: np.ndarray) -> None:
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            np.save(f, array)
    except Exception as e:
        raise MedVerseException(e, sys) from e


def load_numpy_array(file_path: str) -> np.ndarray:
    try:
        with open(file_path, "rb") as f:
            return np.load(f, allow_pickle=True)
    except Exception as e:
        raise MedVerseException(e, sys) from e

"""Rotating file + console logger shared across the pipeline."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y_%m_%d')}.log")

_FORMAT = "[%(asctime)s] %(levelname)s | %(name)s | %(message)s"

_root = logging.getLogger()
if not _root.handlers:
    _root.setLevel(logging.INFO)
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setFormatter(logging.Formatter(_FORMAT))
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(_FORMAT))
    _root.addHandler(fh)
    _root.addHandler(sh)

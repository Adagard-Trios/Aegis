"""Pipeline-wide exception wrapper.

Wrap raised errors with this so the traceback always identifies the file +
line that caused the failure, even after pickling/serialisation through the
training orchestrator.
"""
from __future__ import annotations

import sys
from typing import Optional


class MedVerseException(Exception):
    def __init__(self, error: BaseException | str, error_detail: Optional[object] = None):
        super().__init__(str(error))
        self.error_message = self._build_message(error, error_detail or sys)

    @staticmethod
    def _build_message(error: BaseException | str, error_detail: object) -> str:
        try:
            _, _, exc_tb = error_detail.exc_info()  # type: ignore[attr-defined]
        except Exception:
            exc_tb = None
        if exc_tb is not None:
            file_name = exc_tb.tb_frame.f_code.co_filename
            line = exc_tb.tb_lineno
            return f"Error in [{file_name}] line [{line}]: {error}"
        return f"Error: {error}"

    def __str__(self) -> str:  # pragma: no cover
        return self.error_message

"""
Stub of src.utils.db for the MedVerse AI service.

The real persistence layer lives on the Render backend (snapshots,
history, ledger, alerts). The AI service only needs `insert_interpretation`
because graph_factory writes interpretations into the local DB after
each agent run — here it's a no-op since the AI service is stateless.

If you want interpretations persisted, POST them back to the Render
backend's history endpoint instead of writing locally.
"""
from __future__ import annotations

from typing import Any


def insert_interpretation(
    specialty: str,
    findings: str,
    severity: str = "unknown",
    severity_score: float = 0.0,
    **kwargs: Any,
) -> None:
    """No-op stub. AI service is stateless; persistence lives on Render."""
    return None

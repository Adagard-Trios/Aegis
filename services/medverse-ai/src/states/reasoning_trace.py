"""
Canonical reasoning-step shape.

Every node in the agentic layer (specialty graphs + the new
complex_diagnosis_graph) appends a ReasoningStep dict to the shared
`traces` field on its state. The frontend renders this as the
"chain of thought" view on /diagnostics so a clinician can see exactly
which agent/tool produced which conclusion — and which evidence
disconfirmed which candidate.

We use plain dicts (not Pydantic models) on the wire so LangGraph's
`operator.add` reducer can concatenate them across parallel branches
without serialisation surprises. The TypedDict + helper functions here
just give us a documented, searchable shape.
"""

from __future__ import annotations
from typing import Any, Dict, List, Literal, TypedDict
from datetime import datetime, timezone


StepKind = Literal[
    "analyser",       # deterministic tool/DSP/ML adapter run (Agentic Brain "Analyst")
    "llm",            # LLM call (specialist interpretation, skeptic disconfirm, etc.)
    "planner",        # routing decision — which graphs/agents to run next
    "rag",            # retrieval-augmented context lookup
    "verdict",        # final aggregation step (general_physician, diagnosis_agent)
]


class ReasoningStep(TypedDict, total=False):
    """One row in the reasoning trace.

    `inputs` should hold the *features* the step actually consumed (HR, SpO2,
    QRS-score, etc.) — not the raw 800-sample waveform. Keep it small enough
    to render in a UI tooltip.
    """
    ts: str                       # ISO-8601 UTC, set by append_step
    node: str                     # e.g. "cardiology_node", "skeptic_node"
    kind: StepKind
    inputs: Dict[str, Any]        # features actually used
    outputs: Dict[str, Any]       # the conclusion produced
    confidence: float             # 0.0..1.0 — node's self-rated confidence
    supports: List[str]           # candidate diagnoses this step supports
    contradicts: List[str]        # candidate diagnoses this step disconfirms
    note: str                     # short human-readable summary (for UI rendering)


def make_step(
    node: str,
    kind: StepKind,
    inputs: Dict[str, Any] | None = None,
    outputs: Dict[str, Any] | None = None,
    confidence: float = 1.0,
    supports: List[str] | None = None,
    contradicts: List[str] | None = None,
    note: str = "",
) -> ReasoningStep:
    """Build a ReasoningStep with timestamp + safe defaults.

    The helper exists because TypedDict has no constructor; this also keeps
    timestamping consistent (UTC, ISO-8601, second resolution).
    """
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "node": node,
        "kind": kind,
        "inputs": inputs or {},
        "outputs": outputs or {},
        "confidence": max(0.0, min(1.0, confidence)),
        "supports": supports or [],
        "contradicts": contradicts or [],
        "note": note,
    }

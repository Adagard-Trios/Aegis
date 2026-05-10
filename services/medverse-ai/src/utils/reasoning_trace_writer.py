"""
Tiny helpers for nodes that want to emit ReasoningStep entries +
attach evidence to candidate diagnoses.

Kept separate from src/states/reasoning_trace.py because that file is
state-shape-only (cheap to import from anywhere). This file imports
the full ComplexDiagnosisState shape and a few utilities, so nodes
that don't need them shouldn't pay the import cost.
"""

from __future__ import annotations
from typing import Any, Dict, List, Sequence

from src.states.reasoning_trace import ReasoningStep, StepKind, make_step
from src.states.complex_diagnosis_state import (
    CandidateDiagnosis,
    CandidateEvidence,
    EvidenceVerdict,
)


def trace_step(
    node: str,
    kind: StepKind,
    *,
    inputs: Dict[str, Any] | None = None,
    outputs: Dict[str, Any] | None = None,
    confidence: float = 1.0,
    supports: Sequence[str] = (),
    contradicts: Sequence[str] = (),
    note: str = "",
) -> List[ReasoningStep]:
    """Returns a list with a single trace entry, ready to merge into state.

    Returning a list (not a single dict) is intentional — it matches the
    LangGraph reducer signature on `traces: Annotated[..., operator.add]`,
    so a node body looks like::

        return {"traces": trace_step("skeptic_node", "llm", note="...")}
    """
    return [make_step(node, kind, inputs, outputs, confidence, list(supports), list(contradicts), note)]


def attach_evidence(
    candidates: List[CandidateDiagnosis],
    *,
    candidate_name: str,
    source: str,
    verdict: EvidenceVerdict,
    feature: str,
    weight: float,
    note: str = "",
) -> List[CandidateDiagnosis]:
    """Append one evidence entry to a named candidate (in place + returns the list).

    Adjusts the candidate's score: supporting evidence pulls it toward 1.0,
    contradicting evidence pulls toward 0.0, both proportional to weight.
    Neutral evidence is recorded but doesn't move the score.

    If the named candidate doesn't exist yet, this is a no-op — call
    `propose_candidate` first (or rely on the proposer node having done so).
    """
    ev: CandidateEvidence = {
        "source": source,
        "verdict": verdict,
        "feature": feature,
        "weight": max(0.0, min(1.0, weight)),
        "note": note,
    }
    for c in candidates:
        if c.get("name") == candidate_name:
            c.setdefault("evidence", []).append(ev)
            score = c.get("score", 0.5)
            if verdict == "supports":
                c["score"] = score + (1.0 - score) * ev["weight"]
            elif verdict == "contradicts":
                c["score"] = score * (1.0 - ev["weight"])
            break
    return candidates


def propose_candidate(
    candidates: List[CandidateDiagnosis],
    *,
    name: str,
    rarity: str = "common",
    icd10: str | None = None,
    initial_score: float = 0.3,
    recommended_tests: Sequence[str] = (),
) -> List[CandidateDiagnosis]:
    """Add a candidate if not already present (in place + returns the list)."""
    if any(c.get("name") == name for c in candidates):
        return candidates
    candidates.append({
        "name": name,
        "icd10": icd10,
        "rarity": rarity,  # type: ignore[typeddict-item]
        "score": initial_score,
        "evidence": [],
        "recommended_tests": list(recommended_tests),
    })
    return candidates

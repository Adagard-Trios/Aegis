"""
State schema for the collaborative diagnosis graph.

Mirrors the four-module architecture from the agentic-AI paper:
    Disease Proposer → Rare/Related agents → Background agents → Skeptic → Diagnosis

Each node reads the shared candidate list, attaches evidence/contradictions,
and the final diagnosis_agent_node emits a ranked output. The shared
`traces` field accumulates ReasoningStep dicts so the UI can show the full
chain of reasoning.
"""

from __future__ import annotations
import operator
from typing import Annotated, Any, Dict, List, Literal, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


CandidateRarity = Literal["common", "uncommon", "rare"]
EvidenceVerdict = Literal["supports", "contradicts", "neutral"]


class CandidateEvidence(TypedDict, total=False):
    """One piece of evidence for/against a candidate diagnosis."""
    source: str             # node or analyser that produced it (e.g. "cardiology_node", "fetal_health_adapter")
    verdict: EvidenceVerdict
    feature: str            # which feature drove the verdict (e.g. "HR=145", "fetal_health.label=Pathological")
    weight: float           # 0.0..1.0 — how strongly this evidence pulls the score
    note: str               # short human-readable explanation


class CandidateDiagnosis(TypedDict, total=False):
    """A ranked candidate in the differential.

    `score` is the running probability after all evidence has been applied
    (re-computed by the skeptic + diagnosis nodes). `rarity` lets the UI
    surface rare candidates separately from the common ones, matching the
    paper's Common/Rare Disease agent split.
    """
    name: str               # canonical disease name (e.g. "Atrial fibrillation")
    icd10: Optional[str]    # ICD-10 code if known, else None
    rarity: CandidateRarity
    score: float            # 0.0..1.0 — current probability estimate
    evidence: List[CandidateEvidence]
    recommended_tests: List[str]  # what to do next to disambiguate


def reduce_candidates(
    left: List[CandidateDiagnosis] | None,
    right: List[CandidateDiagnosis] | None,
) -> List[CandidateDiagnosis]:
    """Merge two candidate lists, deduping by name and concatenating evidence.

    Used as the LangGraph reducer when parallel background agents produce
    evidence for the same candidate from different angles. We always keep
    the *highest* score from either side (later nodes can re-score down).
    """
    left = left or []
    right = right or []
    by_name: Dict[str, CandidateDiagnosis] = {}
    for c in left + right:
        name = c.get("name", "")
        if not name:
            continue
        if name not in by_name:
            by_name[name] = {**c, "evidence": list(c.get("evidence") or [])}
        else:
            existing = by_name[name]
            existing["evidence"] = (existing.get("evidence") or []) + list(c.get("evidence") or [])
            existing["score"] = max(existing.get("score", 0.0), c.get("score", 0.0))
            # Prefer non-empty rarity / icd10 if either side filled them
            existing.setdefault("rarity", c.get("rarity", "common"))
            if not existing.get("icd10"):
                existing["icd10"] = c.get("icd10")
            tests = (existing.get("recommended_tests") or []) + (c.get("recommended_tests") or [])
            existing["recommended_tests"] = list(dict.fromkeys(tests))  # dedupe, preserve order
    return list(by_name.values())


class ComplexDiagnosisState(TypedDict, total=False):
    """Shared state for the complex_diagnosis_graph nodes."""

    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Inputs
    patient_id: str
    sensor_telemetry: Dict[str, Any]
    fhir_history: List[Dict[str, Any]]      # prior Observations / DiagnosticReports
    ml_outputs: Dict[str, Any]              # already-computed adapter outputs (passed in by caller)

    # Working set — accumulated across nodes
    candidates: Annotated[List[CandidateDiagnosis], reduce_candidates]
    specialty_findings: Annotated[List[Dict[str, Any]], operator.add]  # selected specialty graphs' outputs

    # Planner decisions
    selected_specialties: List[str]         # which specialty graphs to invoke
    planner_rationale: str

    # Output
    final_ranking: List[CandidateDiagnosis]
    recommended_next_tests: List[str]
    summary_for_clinician: str

    # Reasoning trace (same shape as ExpertSubgraphState.traces)
    traces: Annotated[List[Dict[str, Any]], operator.add]

    # Optional debug
    error_message: Optional[str]

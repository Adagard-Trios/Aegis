"""
Nodes for the collaborative diagnosis graph.

Pattern follows the agentic-AI paper (Disease Proposer + Related/Rare
agents + Skeptic + Diagnosis) plus an Agentic-Brain–style planner that
gates which specialty subgraphs to run instead of always running all 7.

Each node:
- Reads its slice of ComplexDiagnosisState
- Calls deterministic analysers (KB lookup, vital thresholds) or the LLM
- Returns a partial state dict that LangGraph merges via the reducers on
  candidates / specialty_findings / traces

Deterministic vs LLM split:
- Planner, rare_disease_agent, related_disease_finder are deterministic.
- Disease proposer, background_agents, skeptic, diagnosis_agent use the LLM.

This keeps the data-efficient analyser/cognitive-agent separation that the
Agentic-Brain paper advocates and makes the reasoning trace inspectable.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from src.llms.groqllm import GroqLLM
from src.states.complex_diagnosis_state import (
    CandidateDiagnosis,
    ComplexDiagnosisState,
)
from src.utils.rare_disease_kb import find_candidates_by_phenotype
from src.utils.reasoning_trace_writer import (
    attach_evidence,
    propose_candidate,
    trace_step,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# LLM helpers
# ──────────────────────────────────────────────────────────────────────

_model = None


def _get_model():
    """Lazy LLM client. Falls back to None when no Groq key is configured —
    LLM-using nodes degrade to a deterministic stub so the graph still runs."""
    global _model
    if _model is not None:
        return _model
    try:
        _model = GroqLLM().get_llm()
    except Exception as e:
        logger.warning(f"complex_diagnosis: LLM unavailable ({e}); LLM nodes will degrade.")
        _model = False  # sentinel for "tried and failed"
    return _model


# ──────────────────────────────────────────────────────────────────────
# Telemetry -> phenotype text
# ──────────────────────────────────────────────────────────────────────

def _build_phenotype_text(state: ComplexDiagnosisState) -> str:
    """Compress structured telemetry + ML outputs + specialty findings into
    a short natural-language phenotype description suitable for KB
    similarity search and LLM prompting.

    Kept as plain text (not JSON) so it can drop straight into a Chroma
    similarity_search call, and so the LLM doesn't have to parse braces.
    """
    parts: List[str] = []
    tel = state.get("sensor_telemetry") or {}
    vitals = tel.get("vitals") or {}

    if vitals.get("heart_rate"):
        hr = vitals["heart_rate"]
        if hr > 130:
            parts.append(f"Tachycardia (HR {hr})")
        elif hr < 50:
            parts.append(f"Bradycardia (HR {hr})")
        else:
            parts.append(f"HR {hr}")
    if vitals.get("spo2"):
        spo2 = vitals["spo2"]
        if spo2 < 92:
            parts.append(f"Hypoxemia (SpO2 {spo2}%)")
        else:
            parts.append(f"SpO2 {spo2}%")
    if vitals.get("breathing_rate"):
        br = vitals["breathing_rate"]
        if br > 22:
            parts.append(f"Tachypnea (RR {br})")
        elif br < 8:
            parts.append(f"Bradypnea (RR {br})")
    if vitals.get("hrv_rmssd"):
        parts.append(f"HRV RMSSD {vitals['hrv_rmssd']} ms")

    temp = tel.get("temperature") or {}
    if temp.get("cervical"):
        t = temp["cervical"]
        if t > 38.0:
            parts.append(f"Fever ({t}°C)")
        elif t < 35.5:
            parts.append(f"Hypothermia ({t}°C)")

    imu_d = tel.get("imu_derived") or {}
    if (imu_d.get("tremor") or {}).get("tremor_flag"):
        parts.append("Tremor flagged on IMU")
    if (imu_d.get("pots") or {}).get("pots_flag"):
        parts.append("POTS pattern on sit-to-stand")
    if (imu_d.get("gait") or {}).get("asymmetry_flag"):
        parts.append("Gait asymmetry")

    fetal = tel.get("fetal") or {}
    dr = fetal.get("dawes_redman") or {}
    if dr:
        if dr.get("decelerations"):
            parts.append(f"Fetal decelerations ({dr['decelerations']})")
        if dr.get("baseline_fhr"):
            fhr = dr["baseline_fhr"]
            if fhr < 110:
                parts.append(f"Fetal bradycardia (FHR {fhr})")
            elif fhr > 160:
                parts.append(f"Fetal tachycardia (FHR {fhr})")
        if dr.get("criteria_met") is False:
            parts.append("Dawes-Redman criteria not met")
    if any(fetal.get("contractions") or []):
        parts.append("Active uterine contractions")

    # ML adapter outputs (caller passes via state.ml_outputs)
    for key, val in (state.get("ml_outputs") or {}).items():
        if isinstance(val, dict):
            label = val.get("label")
            if label:
                parts.append(f"{key}: {label}")

    # Cross-specialty findings already collected
    for f in state.get("specialty_findings") or []:
        if isinstance(f, dict) and f.get("clinical_findings"):
            parts.append(str(f["clinical_findings"])[:200])

    if not parts:
        return "Patient presentation unremarkable on current snapshot."
    return "; ".join(parts)


# ──────────────────────────────────────────────────────────────────────
# 1. Planner — rule-based specialty gating
# ──────────────────────────────────────────────────────────────────────

def planner_node(state: ComplexDiagnosisState) -> Dict[str, Any]:
    """Decides which specialty graphs the parent orchestrator should invoke.

    Rule-based for now (Agentic-Brain RL upgrade is future work). Always
    includes General Physician for synthesis. Selection is recorded in
    state so the parent (patient_graph) can fan out only to those.
    """
    tel = state.get("sensor_telemetry") or {}
    vitals = tel.get("vitals") or {}
    imu_d = tel.get("imu_derived") or {}
    fetal = tel.get("fetal") or {}

    selected: List[str] = []
    rationale_bits: List[str] = []

    hr = vitals.get("heart_rate") or 0
    spo2 = vitals.get("spo2") or 100
    br = vitals.get("breathing_rate") or 0
    hrv = vitals.get("hrv_rmssd") or 50

    if hr > 120 or hr < 50 or hrv < 15:
        selected.append("Cardiology")
        rationale_bits.append(f"HR={hr}, HRV={hrv} -> cardiology")
    if spo2 < 94 or br > 22 or br < 8:
        selected.append("Pulmonary")
        rationale_bits.append(f"SpO2={spo2}, RR={br} -> pulmonary")
    if (imu_d.get("tremor") or {}).get("tremor_flag") or \
       (imu_d.get("pots") or {}).get("pots_flag") or \
       (imu_d.get("gait") or {}).get("asymmetry_flag"):
        selected.append("Neurology")
        rationale_bits.append("IMU biomarkers abnormal -> neurology")
    if fetal.get("dawes_redman") or any(fetal.get("contractions") or []):
        selected.append("Obstetrics")
        rationale_bits.append("Active fetal monitoring -> obstetrics")

    # Always include General Physician for synthesis
    if "General Physician" not in selected:
        selected.append("General Physician")

    # Safety floor: if nothing was specifically triggered, run cardiology + GP
    # so we always have at least one specialist's view.
    if len(selected) == 1:  # only GP added
        selected.insert(0, "Cardiology")
        rationale_bits.append("Default fallback: cardiology + GP")

    rationale = "; ".join(rationale_bits) if rationale_bits else "Default workup"

    return {
        "selected_specialties": selected,
        "planner_rationale": rationale,
        "traces": trace_step(
            "planner_node",
            "planner",
            inputs={"hr": hr, "spo2": spo2, "br": br, "hrv": hrv,
                    "fetal_active": bool(fetal),
                    "imu_flags": [k for k, v in (imu_d or {}).items()
                                  if isinstance(v, dict) and v.get("flag") or v.get(f"{k}_flag")]},
            outputs={"selected": selected, "rationale": rationale},
            confidence=0.85,
            note=f"Selected {len(selected)} graphs",
        ),
    }


# ──────────────────────────────────────────────────────────────────────
# 2. Disease proposer — initial differential via LLM
# ──────────────────────────────────────────────────────────────────────

class _ProposedDifferential(BaseModel):
    candidates: List[Dict[str, Any]] = Field(
        description=(
            "List of candidate diagnoses, each with {name, icd10, rarity "
            "(common|uncommon|rare), initial_score (0..1), brief_rationale}"
        )
    )


def disease_proposer_node(state: ComplexDiagnosisState) -> Dict[str, Any]:
    """LLM proposes 3-7 initial common-or-uncommon candidate diagnoses based on
    the structured features. Rare candidates come from the next node (KB lookup).
    """
    phenotype = _build_phenotype_text(state)
    candidates: List[CandidateDiagnosis] = []

    model = _get_model()
    if model:
        try:
            prompt = (
                "You are a senior internist building an initial differential "
                "diagnosis from continuous-monitoring telemetry.\n\n"
                f"Patient presentation:\n{phenotype}\n\n"
                "Propose 3-7 candidate diagnoses (common to uncommon, NOT rare — "
                "rare disease lookup happens elsewhere). For each, return "
                "name, ICD-10 code if known, rarity tag (common|uncommon), "
                "initial_score 0.0-1.0 (your prior probability before any "
                "specialist evidence), and a one-sentence brief_rationale."
            )
            structured = model.with_structured_output(_ProposedDifferential)
            response = structured.invoke([HumanMessage(content=prompt)])
            if response and getattr(response, "candidates", None):
                for c in response.candidates[:7]:
                    name = (c.get("name") or "").strip()
                    if not name:
                        continue
                    propose_candidate(
                        candidates,
                        name=name,
                        rarity=c.get("rarity", "common"),
                        icd10=c.get("icd10"),
                        initial_score=float(c.get("initial_score") or 0.4),
                    )
        except Exception as e:
            logger.warning(f"disease_proposer LLM failed: {e}; falling back to phenotype heuristics")

    # Heuristic fallback when LLM is unavailable so the graph still emits
    # something the downstream nodes can refine.
    if not candidates:
        if "Tachycardia" in phenotype:
            propose_candidate(candidates, name="Sinus tachycardia", rarity="common", initial_score=0.5)
        if "Hypoxemia" in phenotype:
            propose_candidate(candidates, name="Hypoxia of unclear cause", rarity="common", initial_score=0.5)
        if "Fetal" in phenotype:
            propose_candidate(candidates, name="Non-reassuring fetal status", rarity="common", initial_score=0.5)

    return {
        "candidates": candidates,
        "traces": trace_step(
            "disease_proposer_node",
            "llm" if model else "analyser",
            inputs={"phenotype": phenotype[:200]},
            outputs={"proposed": [c["name"] for c in candidates]},
            confidence=0.7 if model else 0.4,
            note=f"Initial differential — {len(candidates)} candidates",
        ),
    }


# ──────────────────────────────────────────────────────────────────────
# 3. Rare-disease agent — KB-driven phenotype lookup
# ──────────────────────────────────────────────────────────────────────

def rare_disease_agent_node(state: ComplexDiagnosisState) -> Dict[str, Any]:
    """Adds rare candidates to the differential via Chroma similarity on
    the bundled rare_diseases.jsonl. No LLM in this node — pure KB lookup,
    matching the paper's 'Rare Disease Agent' module."""
    phenotype = _build_phenotype_text(state)
    hits = find_candidates_by_phenotype(phenotype, k=3)

    candidates: List[CandidateDiagnosis] = []
    for h in hits:
        propose_candidate(
            candidates,
            name=h["name"],
            rarity=h.get("rarity", "rare"),
            icd10=h.get("icd10"),
            initial_score=max(0.15, 0.40 - 0.06 * h.get("similarity_rank", 0)),
        )

    return {
        "candidates": candidates,
        "traces": trace_step(
            "rare_disease_agent_node",
            "rag",
            inputs={"phenotype": phenotype[:200], "k": 3},
            outputs={"hits": [h["name"] for h in hits]},
            confidence=0.6 if hits else 0.2,
            note=f"KB returned {len(hits)} candidates",
        ),
    }


# ──────────────────────────────────────────────────────────────────────
# 4. Related-disease finder — KB-similarity expansion of confusables
# ──────────────────────────────────────────────────────────────────────

def related_disease_finder_node(state: ComplexDiagnosisState) -> Dict[str, Any]:
    """For each existing candidate, look up adjacent/confusable conditions in
    the KB and add the highest-similarity ones. Catches diagnoses that the
    proposer might have missed because they share a phenotype but the
    initial LLM call didn't surface them."""
    existing_names = {c.get("name") for c in (state.get("candidates") or [])}
    additions: List[CandidateDiagnosis] = []
    note_bits: List[str] = []

    for c in (state.get("candidates") or []):
        name = c.get("name") or ""
        if not name:
            continue
        # Use the candidate's own name + rarity as a query for "things often
        # confused with this" — phenotypes overlap on similar-sounding entries
        hits = find_candidates_by_phenotype(name, k=3)
        for h in hits:
            if h["name"] in existing_names or h["name"] == name:
                continue
            propose_candidate(
                additions,
                name=h["name"],
                rarity=h.get("rarity", "uncommon"),
                icd10=h.get("icd10"),
                initial_score=0.20,
            )
            existing_names.add(h["name"])
            note_bits.append(f"{name}->{h['name']}")
            break  # one related candidate per existing entry to avoid bloat

    return {
        "candidates": additions,
        "traces": trace_step(
            "related_disease_finder_node",
            "rag",
            inputs={"existing_count": len(existing_names) - len(additions)},
            outputs={"added": [a["name"] for a in additions]},
            confidence=0.55,
            note="; ".join(note_bits) or "no related candidates added",
        ),
    }


# ──────────────────────────────────────────────────────────────────────
# 5. Background agents — per-candidate evidence gather (LLM)
# ──────────────────────────────────────────────────────────────────────

class _CandidateEvidenceBatch(BaseModel):
    items: List[Dict[str, Any]] = Field(
        description=(
            "For each candidate, a list of evidence items: "
            "{candidate_name, verdict (supports|contradicts|neutral), "
            "feature, weight 0..1, note}"
        )
    )


def background_agents_node(state: ComplexDiagnosisState) -> Dict[str, Any]:
    """One LLM call enriches every candidate with supporting/contradicting
    evidence drawn from the patient's vitals + ML outputs + specialty
    findings. Mirrors the paper's parallel "Background Agent" fan-out
    collapsed into a single batched call (cheaper, same effect for our
    typical 5-10 candidates)."""
    candidates: List[CandidateDiagnosis] = list(state.get("candidates") or [])
    if not candidates:
        return {"traces": trace_step("background_agents_node", "llm",
                                     note="no candidates to evaluate")}

    phenotype = _build_phenotype_text(state)
    model = _get_model()
    note = "no LLM"

    if model:
        try:
            cand_summary = "\n".join(
                f"- {c['name']} (rarity={c.get('rarity', 'common')}, current_score={c.get('score', 0):.2f})"
                for c in candidates
            )
            prompt = (
                "For each candidate diagnosis, evaluate whether the patient's "
                "current presentation supports, contradicts, or is neutral "
                "toward it. Use only the features listed.\n\n"
                f"Patient features: {phenotype}\n\n"
                f"Candidates:\n{cand_summary}\n\n"
                "For each, return one or more evidence items with:\n"
                "  candidate_name (must match exactly), verdict, feature, "
                "weight 0..1 (your confidence), note (one short sentence)."
            )
            structured = model.with_structured_output(_CandidateEvidenceBatch)
            response = structured.invoke([HumanMessage(content=prompt)])
            if response and getattr(response, "items", None):
                for item in response.items:
                    name = (item.get("candidate_name") or "").strip()
                    verdict = item.get("verdict") or "neutral"
                    if verdict not in ("supports", "contradicts", "neutral"):
                        verdict = "neutral"
                    attach_evidence(
                        candidates,
                        candidate_name=name,
                        source="background_agents",
                        verdict=verdict,  # type: ignore[arg-type]
                        feature=item.get("feature", ""),
                        weight=float(item.get("weight") or 0.3),
                        note=item.get("note", ""),
                    )
                note = f"attached {len(response.items)} evidence items"
        except Exception as e:
            logger.warning(f"background_agents LLM failed: {e}")
            note = f"LLM error: {e}"

    return {
        "candidates": candidates,
        "traces": trace_step(
            "background_agents_node",
            "llm" if model else "analyser",
            inputs={"candidates": [c["name"] for c in candidates], "phenotype": phenotype[:200]},
            outputs={"updated_scores": {c["name"]: round(c.get("score", 0), 2) for c in candidates}},
            confidence=0.75 if model else 0.3,
            note=note,
        ),
    }


# ──────────────────────────────────────────────────────────────────────
# 6. Skeptic — actively disconfirm each candidate (LLM)
# ──────────────────────────────────────────────────────────────────────

class _SkepticVerdicts(BaseModel):
    verdicts: List[Dict[str, Any]] = Field(
        description=(
            "For each candidate, your skeptical assessment: "
            "{candidate_name, top_disconfirmer (feature that argues against), "
            "weight 0..1 (how strong the disconfirmation), note (one sentence)}. "
            "Skip candidates you cannot meaningfully disconfirm."
        )
    )


def skeptic_node(state: ComplexDiagnosisState) -> Dict[str, Any]:
    """The Skeptic. Asks the LLM to play devil's advocate against each
    candidate using only the available data; attaches contradicting
    evidence. Pulls scores down on candidates the patient's data fails
    to support, which surfaces real diagnoses by elimination."""
    candidates: List[CandidateDiagnosis] = list(state.get("candidates") or [])
    if not candidates:
        return {"traces": trace_step("skeptic_node", "llm", note="no candidates to disconfirm")}

    phenotype = _build_phenotype_text(state)
    model = _get_model()
    note = "no LLM"

    if model:
        try:
            cand_lines = "\n".join(f"- {c['name']}" for c in candidates)
            prompt = (
                "You are the Skeptic. For each candidate diagnosis, identify "
                "the single strongest feature that argues AGAINST it given "
                "the patient's current presentation. Be conservative: only "
                "disconfirm when the evidence genuinely cuts against the "
                "diagnosis.\n\n"
                f"Patient features: {phenotype}\n\n"
                f"Candidates:\n{cand_lines}\n\n"
                "Skip any candidate you cannot meaningfully disconfirm."
            )
            structured = model.with_structured_output(_SkepticVerdicts)
            response = structured.invoke([HumanMessage(content=prompt)])
            if response and getattr(response, "verdicts", None):
                for v in response.verdicts:
                    name = (v.get("candidate_name") or "").strip()
                    if not name:
                        continue
                    attach_evidence(
                        candidates,
                        candidate_name=name,
                        source="skeptic",
                        verdict="contradicts",
                        feature=v.get("top_disconfirmer", ""),
                        weight=float(v.get("weight") or 0.3),
                        note=v.get("note", ""),
                    )
                note = f"disconfirmed {len(response.verdicts)} candidates"
        except Exception as e:
            logger.warning(f"skeptic_node LLM failed: {e}")
            note = f"LLM error: {e}"

    return {
        "candidates": candidates,
        "traces": trace_step(
            "skeptic_node",
            "llm" if model else "analyser",
            outputs={"final_scores": {c["name"]: round(c.get("score", 0), 2) for c in candidates}},
            confidence=0.7 if model else 0.2,
            note=note,
        ),
    }


# ──────────────────────────────────────────────────────────────────────
# 7. Diagnosis agent — final ranking + recommended next tests (LLM)
# ──────────────────────────────────────────────────────────────────────

class _FinalRanking(BaseModel):
    ranking: List[Dict[str, Any]] = Field(
        description=(
            "Top 3-5 candidates ranked by likelihood, each with "
            "{name, rank 1..N, justification (which evidence drove it)}"
        )
    )
    recommended_next_tests: List[str] = Field(
        description="Up to 5 specific tests/observations that would best disambiguate."
    )
    summary_for_clinician: str = Field(
        description="Two-to-three sentence narrative for the doctor's eyes."
    )


def diagnosis_agent_node(state: ComplexDiagnosisState) -> Dict[str, Any]:
    """Final synthesis. Reads candidates + their evidence and produces a
    ranked output + recommended workup. The score-based ordering is the
    deterministic baseline; the LLM may override with clinical judgment
    (and we record both in the trace so the clinician can audit)."""
    candidates: List[CandidateDiagnosis] = list(state.get("candidates") or [])

    # Deterministic baseline ranking — by current score
    by_score = sorted(candidates, key=lambda c: c.get("score", 0), reverse=True)
    summary = ""
    next_tests: List[str] = []
    final_ranking: List[CandidateDiagnosis] = by_score[:5]

    model = _get_model()
    if model and candidates:
        try:
            evidence_blob = []
            for c in by_score[:8]:  # cap LLM context
                ev_str = "; ".join(
                    f"{e.get('verdict', '')}({e.get('feature', '')}, w={e.get('weight', 0):.1f})"
                    for e in (c.get("evidence") or [])
                )
                evidence_blob.append(
                    f"- {c['name']} (score={c.get('score', 0):.2f}, rarity={c.get('rarity', '')})\n"
                    f"    evidence: {ev_str or 'none'}"
                )
            prompt = (
                "Rank the most likely diagnoses given the assembled evidence. "
                "Then recommend 2-5 specific tests or observations that "
                "would best disambiguate the top candidates. Finish with a "
                "2-3 sentence narrative summary for the clinician.\n\n"
                f"Candidates and evidence:\n{chr(10).join(evidence_blob)}"
            )
            structured = model.with_structured_output(_FinalRanking)
            response = structured.invoke([HumanMessage(content=prompt)])
            if response:
                # Re-order final_ranking to match LLM ranking when names line up
                if getattr(response, "ranking", None):
                    by_name = {c["name"]: c for c in candidates}
                    reordered: List[CandidateDiagnosis] = []
                    for r in response.ranking[:5]:
                        n = (r.get("name") or "").strip()
                        if n in by_name:
                            reordered.append(by_name[n])
                    if reordered:
                        final_ranking = reordered
                next_tests = list(response.recommended_next_tests or [])[:5]
                summary = (response.summary_for_clinician or "").strip()
        except Exception as e:
            logger.warning(f"diagnosis_agent LLM failed: {e}")

    if not summary:
        if final_ranking:
            top = final_ranking[0]
            summary = (
                f"Top candidate: {top['name']} (score {top.get('score', 0):.2f}). "
                f"{len(final_ranking)} ranked candidates total. "
                f"LLM synthesis unavailable — score-based ordering."
            )
        else:
            summary = "No candidates were generated for this snapshot."

    if not next_tests:
        next_tests = ["12-lead ECG", "Basic metabolic panel", "CBC with differential"]

    return {
        "final_ranking": final_ranking,
        "recommended_next_tests": next_tests,
        "summary_for_clinician": summary,
        "traces": trace_step(
            "diagnosis_agent_node",
            "verdict",
            outputs={
                "top_3": [c["name"] for c in final_ranking[:3]],
                "next_tests": next_tests,
            },
            confidence=0.8 if model else 0.4,
            note=summary[:120],
        ),
    }

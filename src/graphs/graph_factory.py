"""
src/graphs/graph_factory.py

Factory function that builds a LangGraph StateGraph for any medical specialty.
Architecture: __start__ → information_retrieval → interpretation_generation → __end__
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph

from src.llms.groqllm import GroqLLM
from src.states.expert_subgraph_state import ExpertSubgraphState
from src.utils.prompts import get_expert_prompt
from src.utils.utils import EXPERT_TOOLS, get_today_str
from src.utils.vector_store import get_history, save_interpretation
from src.utils.db import insert_interpretation


def _augment_with_ml_models(specialty: str, telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attach structured-model outputs (ECGFounder, respiratory CNN, fetal
    health, retinal classifiers, …) to the tool_results dict when the
    relevant adapter has weights loaded and the telemetry snapshot
    carries the inputs the adapter needs.

    Returns a dict of extra {tool_name: json_string} entries — empty when
    no adapters are ready or no relevant inputs are present.

    Each branch gates on (a) specialty match, (b) adapter.is_loaded, and
    (c) snapshot contains the right modality data. Each adapter call is
    wrapped in try/except so a single broken weight file can never break
    the whole graph run.
    """
    extras: Dict[str, str] = {}
    telemetry = telemetry or {}
    waveform = telemetry.get("waveform") or {}

    import numpy as np

    # ── Cardiology ───────────────────────────────────────────────────
    if "Cardiology" in specialty:
        if waveform:
            try:
                from src.ml.ecgfounder_adapter import get_ecgfounder
                adapter = get_ecgfounder()
                if adapter.is_loaded and waveform.get("ecg_lead2"):
                    signal = np.asarray(waveform["ecg_lead2"], dtype=float)
                    pred = adapter.classify(signal, fs=waveform.get("fs", 40))
                    if pred is not None:
                        extras["ecgfounder_classification"] = json.dumps(pred)
            except Exception:
                pass

    # ── Pulmonary ────────────────────────────────────────────────────
    if "Pulmonary" in specialty or "Respiratory" in specialty:
        if waveform:
            try:
                from src.ml.pulmonary_classifier import get_pulmonary_classifier
                clf = get_pulmonary_classifier()
                if clf.is_loaded and waveform.get("audio"):
                    audio = np.asarray(waveform["audio"], dtype=float)
                    pred = clf.predict(audio, fs=waveform.get("fs", 40))
                    if pred is not None:
                        extras["respiratory_cnn_classification"] = json.dumps({
                            "label": pred.label,
                            "probs": pred.probs,
                            "confidence": pred.confidence,
                        })
            except Exception:
                pass

    # ── Obstetrics: fetal_health + preterm_labour ────────────────────
    if "Obstetrics" in specialty or "Gynecology" in specialty:
        fetal_block = telemetry.get("fetal") or {}
        if fetal_block:
            try:
                from src.ml.fetal_health_adapter import get_fetal_health
                adapter = get_fetal_health()
                if adapter.is_loaded:
                    pred = adapter.predict_dict(fetal_block)
                    if pred is not None:
                        extras["fetal_health_prediction"] = json.dumps(pred)
            except Exception:
                pass
            try:
                from src.ml.preterm_labour_adapter import get_preterm_labour
                adapter = get_preterm_labour()
                if adapter.is_loaded:
                    pred = adapter.predict_dict({
                        "fetal": fetal_block,
                        "patient": telemetry.get("patient") or {},
                    })
                    if pred is not None:
                        extras["preterm_labour_prediction"] = json.dumps(pred)
            except Exception:
                pass

    # ── Ocular: retinal_disease + retinal_age ────────────────────────
    if "Ocular" in specialty or "Ocul" in specialty:
        imaging = telemetry.get("imaging") or {}
        retinal_path = (imaging.get("retinal") or {}).get("image_path")
        demographics = telemetry.get("patient") or {}
        if demographics or retinal_path:
            try:
                from src.ml.retinal_disease_adapter import get_retinal_disease
                adapter = get_retinal_disease()
                if adapter.is_loaded:
                    pred = adapter.predict_with_image(demographics, image_path=retinal_path)
                    if pred is not None:
                        extras["retinal_disease_prediction"] = json.dumps(pred)
            except Exception:
                pass
            try:
                from src.ml.retinal_age_adapter import get_retinal_age
                adapter = get_retinal_age()
                if adapter.is_loaded:
                    pred = adapter.predict_with_image(demographics, image_path=retinal_path)
                    if pred is not None:
                        extras["retinal_age_prediction"] = json.dumps(pred)
            except Exception:
                pass

    return extras

def _get_model(specialty: str = None):
    # Cannot cache globally if different specialties use different keys!
    return GroqLLM(specialty).get_llm()


# ─── Node Factories ─────────────────────────────────────────────────────────


def _make_information_retrieval(specialty: str):
    """
    Creates the information_retrieval node for a given specialty.
    Calls all tools registered for that specialty in parallel (mock),
    collects results into state.tool_results.
    """
    tools = EXPERT_TOOLS.get(specialty, [])

    def information_retrieval(state: ExpertSubgraphState) -> Dict[str, Any]:
        tool_results: Dict[str, str] = {}

        # Call each tool and collect results
        for tool_fn in tools:
            try:
                result = tool_fn.invoke({})
                tool_results[tool_fn.name] = result
            except Exception as e:
                tool_results[tool_fn.name] = f"ERROR: {e}"

        # Augment with structured ML-model outputs when adapters are loaded
        try:
            telemetry = state.get("sensor_telemetry") or {}
            ml_extras = _augment_with_ml_models(specialty, telemetry)
            tool_results.update(ml_extras)
        except Exception:
            pass

        return {
            "tool_results": tool_results,
            "messages": [
                AIMessage(
                    content=f"[{specialty}] Information retrieval complete. "
                    f"{len(tool_results)} tools executed."
                )
            ],
            "traces": [
                {
                    "step": "information_retrieval",
                    "specialty": specialty,
                    "tools_called": list(tool_results.keys()),
                }
            ],
        }

    return information_retrieval


def _make_interpretation_generation(specialty: str):
    """
    Creates the interpretation_generation node for a given specialty.
    Loads domain knowledge + session history, calls LLM with comprehensive
    system prompt, saves output summary to vector store.
    """

    def interpretation_generation(state: ExpertSubgraphState) -> Dict[str, Any]:
        domain = state.get("expert_domain") or specialty
        tool_results = state.get("tool_results") or {}
        shared = state.get("shared_context") or {}
        telemetry = state.get("sensor_telemetry") or {}

        # Format tool results for the prompt
        tool_results_str = "\n".join(
            [f"### {name}\n```json\n{result}\n```" for name, result in tool_results.items()]
        )

        # Get patient ID for history lookup (from shared context or default)
        patient_id = shared.get("patient_id", "default_patient")

        # Retrieve past session history from vector store
        history = get_history(
            specialty=specialty,
            patient_id=patient_id,
            query=f"{domain} assessment current session",
            k=5,
        )

        # Build the patient profile string
        patient_profile = shared.get("patient_base", "")
        if isinstance(patient_profile, dict):
            patient_profile = json.dumps(patient_profile, indent=2)

        # Telemetry context
        telemetry_str = json.dumps(telemetry, indent=2) if telemetry else ""

        # Assemble the full system prompt
        system_prompt = get_expert_prompt(
            specialty=specialty,
            tool_results=tool_results_str,
            history=history if history else None,
            patient_profile=str(patient_profile),
            telemetry_context=telemetry_str,
        )

        # Call the LLM
        try:
            resp = _get_model(specialty).invoke(
                [HumanMessage(content=system_prompt)]
            )
            content = getattr(resp, "content", None) or str(resp)
        except Exception as e:
            return {
                "error_message": f"{type(e).__name__}: {e}",
                "final_expert_analysis": {
                    "expert_domain": domain,
                    "clinical_findings": f"Interpretation failed: {e}",
                    "anomaly_detected": False,
                    "confidence_score": 0.0,
                },
                "messages": [
                    AIMessage(content=f"[{domain}] Interpretation generation failed.")
                ],
            }

        # Parse the LLM response (robust JSON extraction)
        try:
            import re
            content_clean = content.strip()
            # Greedy match from first { to last }
            json_match = re.search(r'\{.*\}', content_clean, re.DOTALL)
            
            clean = json_match.group(0) if json_match else content_clean
            parsed = json.loads(clean)
        except (json.JSONDecodeError, Exception):
            parsed = {
                "expert": domain,
                "finding": content.strip()[:1000] + "..." if len(content) > 1000 else content.strip(),
                "severity": "unknown",
                "severity_score": 0.0,
                "confidence": 0.5,
            }

        # Build the final analysis
        analysis = {
            "expert_domain": domain,
            "clinical_findings": parsed.get("finding", content),
            "severity": parsed.get("severity", "unknown"),
            "severity_score": parsed.get("severity_score", 0.0),
            "key_observations": parsed.get("key_observations", []),
            "recommendations": parsed.get("recommendations", []),
            "confidence_score": parsed.get("confidence", 0.6),
            "anomaly_detected": parsed.get("severity_score", 0) >= 5,
            "generated_at": get_today_str(),
        }

        # Save interpretation summary to vector store for future sessions
        summary = (
            f"[{domain}] Severity: {analysis['severity']} "
            f"(score: {analysis['severity_score']}). "
            f"Findings: {analysis['clinical_findings'][:300]}"
        )
        try:
            save_interpretation(
                specialty=specialty,
                patient_id=patient_id,
                interpretation=content,
                summary=summary,
                metadata={
                    "severity": analysis["severity"],
                    "severity_score": analysis["severity_score"],
                    "generated_at": analysis["generated_at"],
                },
            )
        except Exception:
            pass  # Don't fail the node if vector store write fails
            
        try:
            insert_interpretation(
                specialty=specialty,
                findings=analysis["clinical_findings"],
                severity=analysis["severity"],
                severity_score=analysis["severity_score"]
            )
        except Exception:
            pass

        return {
            "final_expert_analysis": analysis,
            "messages": [
                AIMessage(content=analysis['clinical_findings'].strip())
            ],
            "traces": [
                {
                    "step": "interpretation_generation",
                    "specialty": specialty,
                    "severity": analysis["severity"],
                    "severity_score": analysis["severity_score"],
                }
            ],
        }

    return interpretation_generation


# ─── Graph Builder ───────────────────────────────────────────────────────────


def build_expert_graph(specialty: str) -> StateGraph:
    """
    Build a LangGraph StateGraph for a given medical specialty.

    Architecture:
        __start__ → information_retrieval → interpretation_generation → __end__

    Args:
        specialty: Key from EXPERT_TOOLS / EXPERT_SYSTEM_PROMPTS

    Returns:
        Uncompiled StateGraph ready for .compile()
    """
    builder = StateGraph(ExpertSubgraphState)

    # Create specialty-specific node functions
    info_retrieval = _make_information_retrieval(specialty)
    interpretation = _make_interpretation_generation(specialty)

    # Add nodes
    builder.add_node("information_retrieval", info_retrieval)
    builder.add_node("interpretation_generation", interpretation)

    # Wire edges
    builder.add_edge("__start__", "information_retrieval")
    builder.add_edge("information_retrieval", "interpretation_generation")
    builder.add_edge("interpretation_generation", END)

    return builder

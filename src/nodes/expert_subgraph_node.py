from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph

from src.llms.groqllm import GroqLLM
from src.states.expert_subgraph_state import ExpertSubgraphState
from src.utils.utils import get_today_str


_model = None


def _get_model():
    global _model
    if _model is None:
        _model = GroqLLM().get_llm()
    return _model


def expert_analysis(state: ExpertSubgraphState) -> Dict[str, Any]:
    domain = state.get("expert_domain") or "General"
    telemetry = state.get("sensor_telemetry") or {}
    shared = state.get("shared_context") or {}

    prompt = (
        "You are a medical specialist agent.\n"
        f"Specialty: {domain}\n"
        f"Date: {get_today_str()}\n\n"
        "Context:\n"
        f"{shared}\n\n"
        "Telemetry:\n"
        f"{telemetry}\n\n"
        "Return a concise expert assessment with findings, anomaly flag, and confidence."
    )

    # Keep it robust: if the LLM errors or returns empty, still return a stable shape.
    try:
        resp = _get_model().invoke([HumanMessage(content=prompt)])
        content = getattr(resp, "content", None) or str(resp)
    except Exception as e:  # noqa: BLE001
        return {
            "error_message": f"{type(e).__name__}: {e}",
            "final_expert_analysis": {
                "expert_domain": domain,
                "clinical_findings": "Expert analysis failed.",
                "anomaly_detected": False,
                "confidence_score": 0.0,
            },
            "messages": [AIMessage(content=f"[{domain}] Expert analysis failed.")],
        }

    analysis = {
        "expert_domain": domain,
        "clinical_findings": content,
        "anomaly_detected": False,
        "confidence_score": 0.6,
        "generated_at": get_today_str(),
    }

    return {
        "final_expert_analysis": analysis,
        "messages": [AIMessage(content=f"[{domain}] Expert analysis complete.")],
        "traces": [{"step": "expert_analysis", "domain": domain}],
    }


def create_expert_subgraph() -> StateGraph:
    builder = StateGraph(ExpertSubgraphState)
    builder.add_node("expert_analysis", expert_analysis)
    builder.add_edge("__start__", "expert_analysis")
    builder.add_edge("expert_analysis", END)
    return builder


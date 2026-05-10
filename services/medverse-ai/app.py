"""
MedVerse AI service — Hugging Face Spaces deployment.

Hosts only the LangGraph + Groq agent endpoints. The main MedVerse
backend on Render free tier (512 MB RAM) cannot fit LangGraph in
memory, so all `/api/agent/*` calls are routed here instead.

Endpoints:
  - GET  /health                  → liveness probe
  - GET  /health/diagnostics      → flags, secrets, Groq client check
  - POST /api/agent/ask           → synchronous expert-graph invocation
  - POST /api/agent/run-now       → fan out across all 7 specialties
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()  # picks up .env when run locally; HF Spaces env vars override

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ─── App + CORS ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="MedVerse AI",
    description="LangGraph specialty-expert agent endpoints, deployed off the main API to fit free-tier RAM ceilings.",
    version="0.1.0",
)

# Open CORS — this service is called from the mobile app (no CORS impact)
# and the Next.js dashboard (full CORS needed). Restrict via the
# MEDVERSE_AI_CORS_ORIGINS env var when shipping to a known frontend.
_cors_env = (os.environ.get("MEDVERSE_AI_CORS_ORIGINS") or "").strip()
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Specialty resolution ───────────────────────────────────────────────────

# Same mapping the main backend uses — keep these strings in sync.
_SPECIALTY_ALIASES = {
    "cardiology": "Cardiology Expert",
    "cardiac": "Cardiology Expert",
    "pulmonary": "Pulmonology Expert",
    "pulmonology": "Pulmonology Expert",
    "respiratory": "Pulmonology Expert",
    "neurology": "Neurology Expert",
    "neuro": "Neurology Expert",
    "dermatology": "Dermatology Expert",
    "skin": "Dermatology Expert",
    "obstetrics": "Obstetrics Expert",
    "gynecology": "Obstetrics Expert",
    "gyno": "Obstetrics Expert",
    "ob": "Obstetrics Expert",
    "ocular": "Ocular Expert",
    "eye": "Ocular Expert",
    "ophthalmology": "Ocular Expert",
    "general_physician": "General Physician",
    "gp": "General Physician",
    "general": "General Physician",
}

ALL_SPECIALTIES = [
    "Cardiology Expert",
    "Pulmonology Expert",
    "Neurology Expert",
    "Dermatology Expert",
    "Obstetrics Expert",
    "Ocular Expert",
    "General Physician",
]


def _resolve_specialty(value: Optional[str]) -> str:
    if not value:
        return "General Physician"
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    return _SPECIALTY_ALIASES.get(v, value if value in ALL_SPECIALTIES else "General Physician")


# ─── Request models ─────────────────────────────────────────────────────────


class AgentAskRequest(BaseModel):
    specialty: Optional[str] = None
    message: str
    snapshot: Optional[Dict[str, Any]] = None
    patient_id: Optional[str] = None


class AgentRunNowRequest(BaseModel):
    snapshot: Optional[Dict[str, Any]] = None
    patient_id: Optional[str] = None
    specialties: Optional[List[str]] = None


# ─── Health ─────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok", "service": "medverse-ai"}


@app.get("/health/diagnostics")
async def health_diagnostics():
    """Mirrors the main backend's diagnostics route — booleans only,
    no secret values leaked."""

    def _present(key: str) -> bool:
        return bool((os.environ.get(key) or "").strip())

    groq_ok = False
    groq_err: Optional[str] = None
    try:
        from groq import Groq
        key = (os.environ.get("GROQ_API_KEY") or "").strip()
        if not key:
            groq_err = "GROQ_API_KEY not set"
        else:
            Groq(api_key=key)
            groq_ok = True
    except Exception as e:
        groq_err = str(e)[:200]

    langgraph_ok = False
    langgraph_err: Optional[str] = None
    try:
        from langgraph.graph import StateGraph  # noqa: F401
        from langchain_groq import ChatGroq  # noqa: F401
        langgraph_ok = True
    except Exception as e:
        langgraph_err = str(e)[:200]

    return {
        "status": "ok",
        "service": "medverse-ai",
        "runtime": {"python": sys.version.split()[0]},
        "secrets_present": {
            "GROQ_API_KEY": _present("GROQ_API_KEY"),
            "CARDIOLOGY_EXPERT_GROQ_API_KEY": _present("CARDIOLOGY_EXPERT_GROQ_API_KEY"),
            "PULMONARY_EXPERT_GROQ_API_KEY": _present("PULMONARY_EXPERT_GROQ_API_KEY"),
            "NEUROLOGY_EXPERT_GROQ_API_KEY": _present("NEUROLOGY_EXPERT_GROQ_API_KEY"),
            "DERMATOLOGY_EXPERT_GROQ_API_KEY": _present("DERMATOLOGY_EXPERT_GROQ_API_KEY"),
            "GYNECOLOGY_EXPERT_GROQ_API_KEY": _present("GYNECOLOGY_EXPERT_GROQ_API_KEY"),
            "OCULOMETRIC_EXPERT_GROQ_API_KEY": _present("OCULOMETRIC_EXPERT_GROQ_API_KEY"),
            "GENERAL_PHYSICIAN_GROQ_API_KEY": _present("GENERAL_PHYSICIAN_GROQ_API_KEY"),
        },
        "groq_client": {"ok": groq_ok, "error": groq_err},
        "langgraph": {"ok": langgraph_ok, "error": langgraph_err},
        "cors_origins": _cors_origins,
    }


# ─── Agent endpoints ────────────────────────────────────────────────────────


def _build_state(message: str, patient_id: str, snapshot: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "messages": [{"role": "user", "content": message}],
        "expert_domain": "",  # set by the graph
        "sensor_telemetry": snapshot or {},
        "shared_context": {
            "patient_id": patient_id or "medverse-demo-patient",
        },
        "tool_results": {},
    }


@app.post("/api/agent/ask")
async def api_agent_ask(req: AgentAskRequest):
    """Synchronous expert-graph invocation. Same shape as the original
    Render endpoint — mobile / dashboard need only swap the host."""
    specialty = _resolve_specialty(req.specialty)
    pid = (req.patient_id or "medverse-demo-patient").strip()
    try:
        from src.graphs.graph_factory import build_expert_graph
        graph = build_expert_graph(specialty).compile()
        state = _build_state(req.message, pid, req.snapshot)
        result = graph.invoke(state)

        reply = ""
        if isinstance(result, dict):
            messages = result.get("messages") or []
            if messages:
                last = messages[-1]
                reply = last.get("content") if isinstance(last, dict) else getattr(last, "content", "")
            reply = reply or str(result.get("interpretation") or result.get("response") or "")

        analysis = (result or {}).get("final_expert_analysis") or {}
        return {
            "reply": reply or "(no response)",
            "severity": analysis.get("severity", (result or {}).get("severity", "normal")),
            "severity_score": analysis.get("severity_score", (result or {}).get("severity_score", 0)),
            "specialty": specialty,
            "key_observations": analysis.get("key_observations", []),
            "recommendations": analysis.get("recommendations", []),
        }
    except Exception as e:
        logger.exception("agent ask failed")
        return {
            "reply": f"Agent unavailable: {e}. Try again in a few seconds.",
            "severity": "normal",
            "severity_score": 0,
            "specialty": specialty,
            "error": str(e)[:300],
        }


@app.post("/api/agent/run-now")
async def api_agent_run_now(req: AgentRunNowRequest):
    """Fan out across all 7 specialties (or the subset requested) and
    return the assessment dict per specialty."""
    pid = (req.patient_id or "medverse-demo-patient").strip()
    targets = req.specialties or ALL_SPECIALTIES
    targets = [_resolve_specialty(t) for t in targets]

    results: Dict[str, Any] = {}
    try:
        from src.graphs.graph_factory import build_expert_graph
    except Exception as e:
        return {"status": "error", "error": f"agent stack unavailable: {e}", "results": {}}

    for spec in targets:
        try:
            graph = build_expert_graph(spec).compile()
            state = _build_state(
                f"Provide a current {spec.replace(' Expert', '').lower()} assessment.",
                pid,
                req.snapshot,
            )
            out = graph.invoke(state)
            analysis = (out or {}).get("final_expert_analysis") or {}
            results[spec] = {
                "severity": analysis.get("severity", "normal"),
                "severity_score": analysis.get("severity_score", 0),
                "findings": analysis.get("clinical_findings", ""),
                "key_observations": analysis.get("key_observations", []),
            }
        except Exception as e:
            logger.warning(f"{spec} failed: {e}")
            results[spec] = {"error": str(e)[:200]}

    return {"status": "ok", "patient_id": pid, "results": results}

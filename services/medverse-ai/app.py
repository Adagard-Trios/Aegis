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
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()  # picks up .env when run locally; HF Spaces env vars override


# ─── Logging ────────────────────────────────────────────────────────────────
#
# Default: human-readable timestamped format for local dev.
# Production: set MEDVERSE_LOG_FORMAT=json on the Space → emits one JSON
# object per record, machine-parseable by HF's log viewer / observability
# pipelines.

class _JsonLogFormatter(logging.Formatter):
    """Minimal JSON log formatter. No external deps (python-json-logger
    isn't worth the dep just for this)."""
    def format(self, record: logging.LogRecord) -> str:
        import json
        out = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str)


def _configure_logging() -> None:
    handler = logging.StreamHandler()
    use_json = (os.environ.get("MEDVERSE_LOG_FORMAT") or "").strip().lower() == "json"
    handler.setFormatter(
        _JsonLogFormatter() if use_json else logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root = logging.getLogger()
    # Strip any handler basicConfig (or the prior import order) added.
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(logging.INFO)


_configure_logging()
logger = logging.getLogger(__name__)


# ─── App + CORS ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="MedVerse AI",
    description="LangGraph specialty-expert agent endpoints, deployed off the main API to fit free-tier RAM ceilings.",
    version="0.1.0",
)

# CORS — defaults to a sensible allowlist (mobile WebView origins,
# the live Render proxy, localhost dev) instead of "*" so a leaked
# Space URL can't be hammered from any browser. Override via the
# MEDVERSE_AI_CORS_ORIGINS env var if you ship a custom frontend.
_DEFAULT_CORS_ORIGINS = [
    "https://medverse-api.onrender.com",
    "http://localhost:3000",
    "http://localhost:8000",
    "capacitor://localhost",   # Capacitor / Ionic shells
    "http://10.0.2.2:8000",    # Android emulator → host
]
_cors_env = (os.environ.get("MEDVERSE_AI_CORS_ORIGINS") or "").strip()
_cors_origins = (
    [o.strip() for o in _cors_env.split(",") if o.strip()]
    or _DEFAULT_CORS_ORIGINS
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ─── Shared API key auth ────────────────────────────────────────────────────
#
# Mobile + Render proxy attach `X-Medverse-Ai-Key: <value>` to every
# /api/agent/* call. Hugging Face Spaces is public, so without this
# anyone with the URL could drain the Groq budget.
#
# Disabled when MEDVERSE_AI_KEY is unset so local dev (`uvicorn app:app
# --reload` without env vars) keeps working — set the env var on the
# Space to lock it down in production.

_AI_KEY_HEADER = "X-Medverse-Ai-Key"
_REQUIRED_AI_KEY = (os.environ.get("MEDVERSE_AI_KEY") or "").strip()


def require_ai_key(request: Request) -> None:
    """FastAPI dependency that 401s when the configured key is missing
    or doesn't match the request header. No-ops when the env var is
    unset (useful for local dev)."""
    if not _REQUIRED_AI_KEY:
        return
    presented = (request.headers.get(_AI_KEY_HEADER) or "").strip()
    if presented != _REQUIRED_AI_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-Medverse-Ai-Key.",
        )


# ─── Rate limit ─────────────────────────────────────────────────────────────
#
# Free Groq tier has request + token caps; a runaway client looping
# /api/agent/ask would burn the budget in seconds. In-memory token
# bucket keyed by API-key value (or by client IP when no key is in use).
# Cap is generous enough for a real demo (30 calls / minute / key) but
# tight enough that an accidental loop trips the brake before billing
# does.

import time
from collections import defaultdict, deque
from threading import Lock as _RLLock

_RATE_LIMIT_PER_MINUTE = int(os.environ.get("MEDVERSE_AI_RATE_PER_MIN") or "30")
_RATE_BUCKETS: Dict[str, "deque[float]"] = defaultdict(deque)
_RATE_LOCK = _RLLock()


def _rate_key(request: Request) -> str:
    """Bucket per AI key when present, else per client IP — so a leaked
    key gets isolated and an unauthenticated demo doesn't share one
    bucket across the world."""
    presented = (request.headers.get(_AI_KEY_HEADER) or "").strip()
    if presented:
        return f"key:{presented}"
    client = request.client
    return f"ip:{client.host}" if client else "ip:unknown"


def rate_limit(request: Request) -> None:
    """Sliding-window 60s rate limit. 429 + Retry-After when exceeded.
    Free tier safety: protects the Groq budget against runaway loops.
    Disabled when MEDVERSE_AI_RATE_PER_MIN<=0."""
    if _RATE_LIMIT_PER_MINUTE <= 0:
        return
    now = time.monotonic()
    cutoff = now - 60.0
    key = _rate_key(request)
    with _RATE_LOCK:
        bucket = _RATE_BUCKETS[key]
        # Drop calls older than 60 s.
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= _RATE_LIMIT_PER_MINUTE:
            # Time until the oldest call ages out → that's when the
            # caller can try again.
            retry_after = max(1, int(60.0 - (now - bucket[0])) + 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded ({_RATE_LIMIT_PER_MINUTE}/min). "
                    f"Try again in {retry_after}s."
                ),
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)


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


class ChatTurn(BaseModel):
    """One prior chat exchange — role is 'user' or 'assistant'."""
    role: str
    content: str


class AgentAskRequest(BaseModel):
    specialty: Optional[str] = None
    message: str
    snapshot: Optional[Dict[str, Any]] = None
    patient_id: Optional[str] = None
    # Multi-turn chat: client sends the recent N turns so the LLM has
    # context for follow-up questions ("can you elaborate on that?"). Cap
    # this on the client (~6 turns is plenty) — we don't enforce here.
    history: Optional[List[ChatTurn]] = None
    # Patient demographics + clinically-relevant notes pulled from
    # mobile's profile_settings_screen. Forwarded into shared_context
    # so the graph can ground answers in who the patient actually is.
    patient_profile: Optional[Dict[str, Any]] = None


class AgentRunNowRequest(BaseModel):
    snapshot: Optional[Dict[str, Any]] = None
    patient_id: Optional[str] = None
    specialties: Optional[List[str]] = None
    patient_profile: Optional[Dict[str, Any]] = None


class ComplexDiagnosisRequest(BaseModel):
    patient_id: Optional[str] = None
    snapshot: Optional[Dict[str, Any]] = None
    fhir_history: Optional[List[Dict[str, Any]]] = None
    patient_profile: Optional[Dict[str, Any]] = None


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

    # ML adapter state — surface which weight pickles loaded so deploy
    # smoke tests can spot a missing/incompatible model without grepping
    # logs. Each accessor wraps in try/except because adapters that
    # hit a heavy import (e.g. ecgfounder needs torch) shouldn't sink
    # the whole diagnostics call.
    adapters: Dict[str, Dict[str, Any]] = {}

    def _probe(name: str, getter):
        try:
            adapter = getter()
            adapters[name] = {
                "is_loaded": bool(getattr(adapter, "is_loaded", False)),
                "weights_path": getattr(adapter, "weights_path", None),
            }
        except Exception as e:
            adapters[name] = {"is_loaded": False, "error": str(e)[:160]}

    # Probe every adapter — all 11 are now sklearn-pickle based
    # (ecgfounder + pulmonary_classifier were rewritten off the
    # PyTorch scaffold so they fire without torch in the image).
    _adapter_probes = [
        ("fetal_health",         "fetal_health_adapter",       "get_fetal_health"),
        ("parkinson_screener",   "parkinson_screener_adapter", "get_parkinson_screener"),
        ("ecg_arrhythmia",       "ecg_arrhythmia_adapter",     "get_ecg_arrhythmia"),
        ("cardiac_age",          "cardiac_age_adapter",        "get_cardiac_age"),
        ("ecgfounder",           "ecgfounder_adapter",         "get_ecgfounder"),
        ("lung_sound",           "lung_sound_adapter",         "get_lung_sound"),
        ("pulmonary_classifier", "pulmonary_classifier",       "get_pulmonary_classifier"),
        ("preterm_labour",       "preterm_labour_adapter",     "get_preterm_labour"),
        ("skin_disease",         "skin_disease_adapter",       "get_skin_disease"),
        ("retinal_disease",      "retinal_disease_adapter",    "get_retinal_disease"),
        ("retinal_age",          "retinal_age_adapter",        "get_retinal_age"),
    ]
    for name, mod_name, fn_name in _adapter_probes:
        try:
            mod = __import__(f"src.ml.{mod_name}", fromlist=[fn_name])
            _probe(name, getattr(mod, fn_name))
        except Exception as e:
            adapters[name] = {"is_loaded": False, "error": f"import: {e}"[:160]}

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
        "ml_adapters": adapters,
        "cors_origins": _cors_origins,
        "ai_key_required": bool(_REQUIRED_AI_KEY),
        "rate_limit_per_min": _RATE_LIMIT_PER_MINUTE,
    }


# ─── Agent endpoints ────────────────────────────────────────────────────────


_PATIENT_DEMOGRAPHIC_KEYS = ("age", "sex", "gestational_age_weeks", "bmi")


def _splice_demographics_into_snapshot(
    snapshot: Dict[str, Any],
    patient_profile: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Mirror profile demographics into `snapshot['patient']` so the
    sklearn adapters in src/ml/ — which look there for `age`, `sex`,
    `gestational_age_weeks`, etc. — find them. Without this splice, every
    cardiology / dermatology / ocular / OB adapter's `_to_feature_row`
    returns nothing and the prediction silently no-ops.

    Doesn't overwrite values the snapshot itself supplied (mobile may
    eventually compute a derived BMI client-side; profile data is the
    fallback)."""
    if not patient_profile:
        return snapshot
    patient_block = dict(snapshot.get("patient") or {})
    for k in _PATIENT_DEMOGRAPHIC_KEYS:
        v = patient_profile.get(k)
        if v in (None, "", []):
            continue
        patient_block.setdefault(k, v)
    if patient_block:
        snapshot = dict(snapshot)  # shallow copy — don't mutate caller's dict
        snapshot["patient"] = patient_block
    return snapshot


def _splice_ctg_analysis(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """When the snapshot carries a raw FHR sample buffer (the abdomen
    monitor's CTG stream), run a stateless Dawes-Redman-lite analysis
    and splice the result into `snapshot['fetal']['dawes_redman']`. The
    fetal_health adapter reads from there + the trained UCI CTG
    preprocessor median-imputes anything the simple analyzer can't
    compute. No-ops cleanly when FHR data is absent."""
    fhr_raw = snapshot.get("fhr_raw") or (snapshot.get("fetal") or {}).get("fhr_raw")
    if not fhr_raw:
        return snapshot
    fetal_block = dict(snapshot.get("fetal") or {})
    # If the client already populated dawes_redman, trust it.
    if fetal_block.get("dawes_redman"):
        return snapshot
    try:
        from src.utils.ctg_lite import analyze as _ctg_analyze
        fetal_block["dawes_redman"] = _ctg_analyze(fhr_raw)
    except Exception as e:
        logger.warning(f"CTG analyze failed: {e}")
        return snapshot
    snapshot = dict(snapshot)
    snapshot["fetal"] = fetal_block
    return snapshot


def _splice_imaging(
    snapshot: Dict[str, Any],
    patient_profile: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Mirror the latest uploaded skin/retinal `image_path` (when
    mobile attached them in the agent request body's
    `patient_profile.imaging` or as top-level keys) into the
    snapshot's `imaging` block. The skin_disease / retinal_disease /
    retinal_age adapters read from there.

    Mobile is the source-of-truth for the latest uploaded image
    paths — when the user uploads via `/api/upload-image` it caches
    the returned path in `LatestImageService` and attaches it to
    every subsequent agent call's `patient_profile.imaging`."""
    if not patient_profile:
        return snapshot
    pp_imaging = patient_profile.get("imaging") if isinstance(patient_profile.get("imaging"), dict) else None
    if not pp_imaging:
        return snapshot
    imaging = dict(snapshot.get("imaging") or {})
    for modality in ("skin", "retinal"):
        path = pp_imaging.get(modality)
        if not path:
            continue
        existing = imaging.get(modality) or {}
        if not existing.get("image_path"):
            imaging[modality] = {**existing, "image_path": path}
    if imaging:
        snapshot = dict(snapshot)
        snapshot["imaging"] = imaging
    return snapshot


def _enrich_snapshot(
    snapshot: Dict[str, Any],
    patient_profile: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Apply all three snapshot enrichments before the graph runs.
    Order is independent — each is a pure functional splice that
    no-ops when its source data isn't present."""
    s = snapshot or {}
    s = _splice_demographics_into_snapshot(s, patient_profile)
    s = _splice_ctg_analysis(s)
    s = _splice_imaging(s, patient_profile)
    return s


def _build_state(
    message: str,
    patient_id: str,
    snapshot: Optional[Dict[str, Any]],
    history: Optional[List[ChatTurn]] = None,
    patient_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble the LangGraph initial state.

    Prior turns from the client are prepended so the graph's reverse-walk
    in interpretation_generation finds the latest user message (the new
    one we just appended) but the LLM still sees the context above it.

    Patient demographics from `patient_profile` are spliced into
    `sensor_telemetry.patient` so the ML adapters that read those keys
    fire instead of silently no-op'ing.
    """
    msgs: List[Dict[str, Any]] = []
    if history:
        for turn in history:
            role = (turn.role or "").strip().lower()
            content = (turn.content or "").strip()
            if not content:
                continue
            # Normalize 'assistant' / 'ai' / 'bot' → 'assistant'; everything
            # else → 'user'. The graph only filters on 'user'/'human'.
            normalized = "assistant" if role in ("assistant", "ai", "bot") else "user"
            msgs.append({"role": normalized, "content": content})
    msgs.append({"role": "user", "content": message})

    shared: Dict[str, Any] = {
        "patient_id": patient_id or "medverse-demo-patient",
    }
    if patient_profile:
        shared["patient_profile"] = patient_profile

    enriched_snapshot = _enrich_snapshot(snapshot or {}, patient_profile)

    return {
        "messages": msgs,
        "expert_domain": "",  # set by the graph
        "sensor_telemetry": enriched_snapshot,
        "shared_context": shared,
        "tool_results": {},
    }


@app.post("/api/agent/ask", dependencies=[Depends(require_ai_key), Depends(rate_limit)])
async def api_agent_ask(req: AgentAskRequest):
    """Synchronous expert-graph invocation. Same shape as the original
    Render endpoint — mobile / dashboard need only swap the host."""
    specialty = _resolve_specialty(req.specialty)
    pid = (req.patient_id or "medverse-demo-patient").strip()
    try:
        from src.graphs.graph_factory import build_expert_graph
        graph = build_expert_graph(specialty).compile()
        state = _build_state(
            req.message,
            pid,
            req.snapshot,
            history=req.history,
            patient_profile=req.patient_profile,
        )
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


@app.post("/api/agent/run-now", dependencies=[Depends(require_ai_key), Depends(rate_limit)])
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
                patient_profile=req.patient_profile,
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


@app.post("/api/agent/complex-diagnosis", dependencies=[Depends(require_ai_key), Depends(rate_limit)])
async def api_agent_complex_diagnosis(req: ComplexDiagnosisRequest):
    """Run the collaborative diagnosis graph (proposer → background →
    skeptic → ranker → diagnoser → narrator). Returns ranked candidate
    diagnoses, recommended next tests, and a clinician-facing summary.
    Latency typically 10-25 s on free CPU (four LLM calls)."""
    pid = (req.patient_id or "medverse-demo-patient").strip()
    snapshot = req.snapshot or {}
    fhir_history = req.fhir_history or []

    try:
        from src.graphs.complex_diagnosis_graph import graph as complex_graph
    except Exception as e:
        logger.exception("complex_diagnosis graph import failed")
        return {
            "status": "graph_unavailable",
            "error": str(e)[:300],
            "patient_id": pid,
        }

    # Same enrichments _build_state applies for /api/agent/ask:
    # demographics → snapshot.patient, FHR raw → snapshot.fetal.dawes_redman,
    # image paths → snapshot.imaging. Each splice no-ops when its source
    # isn't present, so the call is safe for telemetry-only flows.
    enriched_snapshot = _enrich_snapshot(snapshot, req.patient_profile)

    initial_state = {
        "patient_id": pid,
        "patient_profile": req.patient_profile or {},
        "sensor_telemetry": enriched_snapshot,
        "fhir_history": fhir_history,
        "ml_outputs": {},
        "candidates": [],
        "specialty_findings": [],
        "traces": [],
        "messages": [],
    }

    try:
        result = complex_graph.invoke(initial_state)
    except Exception as e:
        logger.exception("complex_diagnosis run failed")
        return {"status": "error", "error": str(e)[:300], "patient_id": pid}

    return {
        "status": "ok",
        "patient_id": pid,
        "selected_specialties": result.get("selected_specialties") or [],
        "planner_rationale": result.get("planner_rationale") or "",
        "candidates": result.get("candidates") or [],
        "final_ranking": result.get("final_ranking") or [],
        "recommended_next_tests": result.get("recommended_next_tests") or [],
        "summary_for_clinician": result.get("summary_for_clinician") or "",
        "traces": result.get("traces") or [],
    }

---
title: MedVerse AI
emoji: 🩺
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: LangGraph specialty-expert agent endpoints for MedVerse
---

# MedVerse AI Service

Hosts the heavy LangGraph + LangChain + Groq stack on **Hugging Face Spaces** (16 GB free RAM, no idle sleep) so the main MedVerse API at Render free tier (512 MB RAM) doesn't OOM on agent calls.

## What it serves

| Method | Path | Purpose |
|---|---|---|
| GET  | `/health` | Liveness probe |
| GET  | `/health/diagnostics` | Reports flag/secret state, Groq client construction |
| POST | `/api/agent/ask` | Synchronous expert-graph invocation per specialty |
| POST | `/api/agent/run-now` | Run all specialty graphs once (fan-out) |

Same request/response shapes as the original Render endpoints — mobile app just points `aiBaseUrl` at this Space's URL.

## Deploying to HF Spaces

1. Create a new HF Space at <https://huggingface.co/new-space>
   - **Owner**: your account
   - **Space name**: `medverse-ai`
   - **License**: pick whatever
   - **SDK**: **Docker** (important — not Streamlit/Gradio)
   - **Hardware**: **CPU basic** (free, 16 GB RAM)
   - **Visibility**: Public (private requires Pro plan)

2. Clone the empty Space locally:
   ```bash
   git clone https://huggingface.co/spaces/<your-username>/medverse-ai
   cd medverse-ai
   ```

3. Copy the contents of this directory (`services/medverse-ai/` from the Aegis repo) into the cloned Space directory and push:
   ```bash
   cp -r /path/to/Aegis/services/medverse-ai/* .
   git add .
   git commit -m "Initial AI service deploy"
   git push
   ```

4. In the HF Space dashboard → **Settings → Variables and secrets**, add:
   ```
   GROQ_API_KEY=<your-key>
   CARDIOLOGY_EXPERT_GROQ_API_KEY=<optional per-specialty key>
   ...
   ```
   At minimum `GROQ_API_KEY` — the per-specialty keys fall back to it.

5. The Space will build automatically (~5–10 min first time). Once "Running":
   ```bash
   curl https://<your-username>-medverse-ai.hf.space/health
   curl https://<your-username>-medverse-ai.hf.space/health/diagnostics
   ```

6. **Update the mobile app**: in `mobile/aegis/lib/services/api_config.dart`, set `_hfSpacesAiUrl` to your Space URL. See the main repo's README → Mobile app → AI service URL section for details.

## Local development

```bash
cd services/medverse-ai
pip install -r requirements.txt
export GROQ_API_KEY=<your-key>
uvicorn app:app --host 0.0.0.0 --port 7860 --reload
```

## What's NOT in this service

Intentionally omitted — not needed for the LLM-only assessment path:
- `src/ml/` adapters (ECGFounder, sklearn classifiers, etc.) — graph_factory's adapter calls degrade silently when imports fail
- Persistence (SQLite + Chroma) — `vector_store.py` writes locally on the Space's ephemeral disk; lost on restart, which is fine because the main Render service owns history
- All endpoints other than `/api/agent/*` and `/health*`

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

## ML adapter status

After every agent call, `graph_factory._augment_with_ml_models` runs the
adapters whose specialty matches and adds their predictions to
`tool_results` for the LLM to ground on. State per adapter:

| Adapter | Specialty | Activates on | Status |
|---|---|---|---|
| `parkinson_screener` | Neurology | `voice_features` dict (22 UCI cols) | ✅ Pickle deployed (real UCI Parkinsons weights) — **inert in this stack** because the vest doesn't capture voice. Add a phone-mic voice-recording flow before this fires. |
| `fetal_health` | Obstetrics | `fetal.dawes_redman` block | ✅ Pickle deployed (real UCI CTG weights) — **fires** when the abdomen monitor is paired and `snapshot.fhr_raw` is present (`src/utils/ctg_lite.analyze` computes the dawes_redman block stateless on each request). |
| `ecg_arrhythmia` | Cardiology | `patient.age` + `patient.sex` + vitals | ⚠ Synthetic baseline pickle — fires on every cardiology call once `Settings → Patient profile → Age + Sex` are filled. |
| `cardiac_age` | Cardiology | `patient.sex` (+ chronological age for delta) | ⚠ Synthetic baseline — same as above |
| `lung_sound` | Pulmonary | `audio.digital_rms` / `audio.analog_rms` | ⚠ Synthetic baseline — fires on every pulmonary call (mobile always sends audio block) |
| `preterm_labour` | Obstetrics | `patient.gestational_age_weeks` + EMG features | ⚠ Synthetic baseline — fires when gestational age is set; EMG fields are imputed by the trained median (no EMG sensor on the vest) |
| `skin_disease` | Dermatology | `patient.age` + `imaging.skin.image_path` | ⚠ Synthetic baseline — fires after the user calls `ApiService.uploadImage(modality: "skin", ...)` once. The path is cached in `LatestImageService` and attached to every subsequent agent call. |
| `retinal_disease` | Ocular | `patient.age` + `patient.sex` + `imaging.retinal.image_path` | ⚠ Synthetic baseline — same flow as skin_disease, modality `"retinal"` |
| `retinal_age` | Ocular | `patient.sex` (+ chronological age for delta) | ⚠ Synthetic baseline |
| `ecgfounder` | Cardiology | `waveform.ecg_lead2` + `fs` | ❌ PyTorch scaffold — `_load_weights()` raises `NotImplementedError`. Drop a `.pt` at `models/ecg/ecgfounder/weights.pt` (e.g. from a HF-published ECGFounder mirror) and override the load method. |
| `pulmonary_classifier` | Pulmonary | `waveform.audio` + `fs` | ❌ PyTorch scaffold — same situation. Drop weights at `models/pulmonary/icbhi_cnn/weights.pt` |

Synthetic baselines are produced by `scripts/train_synthetic_baselines.py` in
the repo root. Each model dir has a `MODEL_CARD.md` explaining the
"DEMO ONLY" caveat. Replace with real-trained weights via
[the workflow in the main repo's README → Future work](../../README.md#future-work).

## What's NOT in this service

Intentionally omitted — not needed for the agent path:
- Persistence (SQLite + Chroma history beyond per-process cache) — `vector_store.py` writes locally on the Space's ephemeral disk; lost on restart, which is fine because the main Render service owns history
- All endpoints other than `/api/agent/*` and `/health*`

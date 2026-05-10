# MedVerse — 5-minute demo

## One-command startup

```bash
./start.sh
```

Boots the FastAPI backend on `:8000` and the Next.js frontend on `:3000` in parallel. Ctrl+C tears both down.

For a hosted version see [Deploy](#deploy) below.

## Prerequisites

| Tool       | Version        | Notes                                              |
|------------|----------------|----------------------------------------------------|
| Python     | 3.13           | `uv sync` or `pip install -r requirements.txt`     |
| Node       | 20+            | `cd frontend && npm install`                       |
| BLE vest   | Optional       | Not required — backend auto-falls-back to mock     |

## 5-minute demo script

Open `http://localhost:3000` and walk through:

1. **00:00 — Home dashboard** *(/)*
   Live vitals tile, vest connection status, FHIR-shaped telemetry pipeline.
   - Talking point: 15 sensors → SSE @ 10 Hz → SQLite + (optional) TimescaleDB.

2. **01:00 — History** *(/history)*
   Resolution toggle (1m / 1h), 4-panel chart (HR, SpO₂, RR, HRV) from the rolled-up backend aggregate.
   - Talking point: same data path runs against TimescaleDB continuous aggregates in prod.

3. **01:45 — Trigger a clinical scenario**
   ```bash
   curl -X POST localhost:8000/api/simulation/scenario \
     -H 'Content-Type: application/json' \
     -d '{"scenario":"hypoxia"}'
   ```
   Watch SpO₂ drop to ~88% and RR rise to ~24 within 2 seconds. The agent fan-out has real data to react to. Other scenarios: `tachycardia`, `fetal_decel`, `arrhythmia`, `normal`.

4. **02:30 — Digital Twin + PK/PD centerpiece** *(/digital-twin)*
   3D anatomical model + the **PK/PD Simulator** panel (top-right).
   - Pick **Labetalol**, dose 50 mg, click **Inject**.
   - The effect-curve chart climbs over ~10 s; HR drops by ~7–8 bpm.
   - Toggle **CYP2D6 → Poor Metabolizer** — the curve flattens (slower elimination, longer tail).
   - Talking point: real two-compartment Bateman equation, genotype-aware k_el modulation.

5. **03:30 — Vest Viewer** *(/vest-viewer)*
   3D vest mesh with live sensor sidebar — direct port of the backend telemetry stream.

6. **04:00 — Expert chat panel**
   Open the bottom-right console — pick a specialty, ask a question. Routes through LangGraph: `patient_graph` → fan-out to `cardiology_graph`, `pulmonary_graph`, `neurology_graph`, `dermatology_graph`, `gynecology_graph`, `ocular_graph` → `general_physician_graph` synthesis.

7. **04:45 — Reset**
   ```bash
   curl -X POST localhost:8000/api/simulation/scenario -d '{"scenario":"normal"}'
   ```

## Endpoints worth knowing

| Endpoint                            | Purpose                                                |
|-------------------------------------|--------------------------------------------------------|
| `GET  /stream`                      | SSE telemetry, 10 Hz                                   |
| `GET  /api/snapshot`                | Single point-in-time vitals snapshot                   |
| `GET  /api/history?resolution=1m`   | Rolled-up time series (HR/SpO₂/RR/HRV)                 |
| `POST /api/simulation/scenario`     | Switch live scenario (`normal` / `tachycardia` / …)    |
| `POST /api/simulation/medicate`     | Inject simulated drug (Bateman PK/PD model)            |
| `POST /api/simulation/cyp2d6`       | Set metabolizer status (`Normal` / `Poor`)             |
| `POST /api/simulation/mode`         | Temporal prediction mode (`Live`, `6h`, `12h`, …)      |
| `GET  /health`                      | Liveness probe (used by Render)                        |

## Deploy

Three free hosts, **$0/mo total**:

```
Mobile + Web frontend
        │
        ├── /api/snapshot/*  /api/history  /api/patients/*  /health  ──► Render free (512 MB)
        │       Data plane: FastAPI core, FHIR, image upload
        │
        └── /api/agent/*  (chat, AI assessments, complex-diagnosis)  ──► HF Spaces free (16 GB)
                AI plane: LangGraph + Chroma + Groq client
```

The split exists because LangGraph + Chroma + sentence-transformers don't fit in Render free's 512 MB. See [README §Cloud deployment](README.md) for the full architecture, env-var reference, and upgrade paths.

### Pre-flight (~10 min)

1. **Rotate Groq API key** at https://console.groq.com/keys. Save the new `gsk_...` value.
2. **Generate two random keys** (JWT secret + AI service shared key):
   ```bash
   python -c "import secrets; print('JWT:', secrets.token_urlsafe(48)); print('AI:', secrets.token_urlsafe(32))"
   ```
3. **(Optional, recommended)** Create a Neon Postgres at https://console.neon.tech (free 3 GB, no expiry) and copy the connection string. Skip to use ephemeral SQLite (wipes on every Render redeploy).

### HF Space (AI plane, ~10 min)

1. https://huggingface.co/new-space → SDK **Docker**, Hardware **CPU basic** (free, 16 GB RAM), Visibility **Public**.
2. **Settings → Variables and secrets** → **New secret**:
   - `GROQ_API_KEY` = your rotated key
   - `MEDVERSE_AI_KEY` = the AI key from pre-flight step 2
3. Generate a Write-scoped HF token at https://huggingface.co/settings/tokens.
4. Push the AI service code:
   ```bash
   HF_USERNAME=<your-username> HF_SPACE=<space-name> HF_TOKEN=hf_xxx ./scripts/deploy-hf.sh
   ```
   First build ~8 min. **Revoke the token immediately after** — see [services/medverse-ai/DEPLOY.md](services/medverse-ai/DEPLOY.md) for token-hygiene notes.
5. Verify:
   ```bash
   curl https://<your-username>-<space-name>.hf.space/health/diagnostics
   ```

### Render (data plane, ~10 min)

1. https://render.com → **New + → Blueprint** → connect this GitHub repo. Render reads [render.yaml](render.yaml) automatically (free plan, Docker runtime, no disk).
2. Set the env vars in the Render dashboard:
   - `GROQ_API_KEY` = your rotated key (only used as fallback when the proxy fails)
   - `MEDVERSE_AI_BASE_URL` = `https://<your-username>-<space-name>.hf.space` (where `/api/agent/*` proxies to)
   - `MEDVERSE_AI_KEY` = same AI key as the Space (proxy attaches it)
   - `MEDVERSE_JWT_SECRET` = JWT secret from pre-flight step 2
   - `MEDVERSE_AUTH_ENABLED=true` (turns on JWT-required mode)
   - `MEDVERSE_DEV_USERNAME=demo` + `MEDVERSE_DEV_PASSWORD=<value>` (the single dev login the API issues tokens for)
   - **(Optional)** `MEDVERSE_DB_URL` = your Neon connection string (leave unset for ephemeral SQLite)
   - **(Optional)** `MEDVERSE_CORS_ORIGINS` = your Vercel URL once that's live
3. **Apply Changes** → first build ~3 min.
4. Verify: `curl https://<render-service>.onrender.com/health/diagnostics` — `groq_client.ok: true`, all flag fields green.

### Vercel (frontend, ~10 min)

1. https://vercel.com → **Add New → Project** → import this repo.
2. **Root Directory** = `frontend` (Vercel offers to detect; confirm).
3. Set environment variables (see [frontend/.env.example](frontend/.env.example)):
   - `NEXT_PUBLIC_API_URL` = your Render URL
   - `NEXT_PUBLIC_AI_URL` = your HF Space URL
   - `NEXT_PUBLIC_AI_KEY` = same AI key as Render + Space
   - `NEXT_PUBLIC_AUTH_REQUIRED=true`
4. Deploy. ~3 min. Push-to-`main` redeploys automatically thereafter.

### Close the loop

Back on Render → set `MEDVERSE_CORS_ORIGINS = https://<your-vercel-url>` → auto-redeploys.

### Verify

| Check | Expected |
|---|---|
| `https://<render-url>/health` | `{"status":"ok","mock":true,"ble_disabled":true}` (~30 s on first request after sleep) |
| `https://<render-url>/health/diagnostics` | All flags green; `groq_client.ok: true`; `db_kind: postgres` if Neon wired |
| `https://<hf-space>.hf.space/health/diagnostics` | `langgraph.ok: true`; both `ml_adapters.*.is_loaded: true`; `ai_key_required: true`; `rate_limit_per_min: 30` |
| `https://<render-url>/api/agent/ask` (POST without `X-Medverse-Ai-Key`) | Render proxy forwards → HF Space → 401 |
| `https://<vercel-url>/login` | Sign-in with `MEDVERSE_DEV_USERNAME` / `_PASSWORD` → Dashboard loads |

## Security defaults

- `MEDVERSE_AUTH_ENABLED=true` in this setup — every `/api/**` route requires a valid Bearer token. JWT issued by `POST /api/auth/login` against the dev creds. Per-patient access control: an authenticated request can't read another user's `patient_id` (returns 403).
- CORS on Render: `MEDVERSE_CORS_ORIGINS` allowlist. CORS on HF Space: defaults to a tight allowlist (Render proxy + localhost), override via `MEDVERSE_AI_CORS_ORIGINS`.
- HF Space rate-limit: 30 calls/min per AI-key (or per IP). Override via `MEDVERSE_AI_RATE_PER_MIN`.
- The JWT secret has no insecure fallback — production startup hard-fails if auth is enabled without a strong secret set.

## Troubleshooting

- **`/stream` is empty** — check `GET /api/status`. If `using_mock=true` the backend never saw a vest; that's fine for the demo.
- **Frontend can't reach the backend** — set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`.
- **PharmacologyPanel chart is flat** — make sure you clicked **Inject**; the panel only renders effect-curve once `pharmacology.active_medication` is set on the snapshot.

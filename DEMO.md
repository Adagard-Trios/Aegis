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

Backend on **Render**, frontend on **Vercel**, database on **Timescale Cloud free tier**. Total monthly cost ~$7 (Render Starter; Vercel + Timescale free tiers).

### Pre-flight (one-time, ~15 min)

1. Rotate the Groq API key at https://console.groq.com/keys. Save the new `gsk_...` value.
2. Generate a JWT secret:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
3. Sign up at https://console.cloud.timescale.com → **Create service** (free tier) → copy the connection string. Replace `postgresql://` with `postgresql+asyncpg://`.

### Render (backend, ~30 min)

1. https://render.com → **New + → Blueprint** → connect this GitHub repo. Render reads [render.yaml](render.yaml) automatically.
2. Set the four `sync: false` env vars in the Render dashboard:
   - `GROQ_API_KEY` = your rotated key
   - `MEDVERSE_JWT_SECRET` = the generated secret
   - `MEDVERSE_DB_URL` = your Timescale Cloud async URL
   - `MEDVERSE_CORS_ORIGINS` = leave blank (you'll fill it after Vercel deploys)
3. **Apply Changes** → first build ~5 min.
4. Run the schema migration once: Render dashboard → **Shell** → `alembic upgrade head`.
5. Copy the Render URL (e.g., `https://medverse-api.onrender.com`).

### Vercel (frontend, ~10 min)

1. https://vercel.com → **Add New → Project** → import this repo.
2. **Root Directory** = `frontend` (Vercel offers to detect; confirm).
3. Set environment variable: `NEXT_PUBLIC_API_URL` = your Render URL from step 5 above.
4. Deploy. ~3 min. Push-to-`main` redeploys automatically thereafter.
5. Copy the Vercel URL.

### Close the loop

Back in the Render dashboard, set `MEDVERSE_CORS_ORIGINS = https://<your-vercel-url>` → Render auto-redeploys.

### Verify

| Check | Expected |
|---|---|
| `https://<render-url>/health` | `{"status":"ok","mock":true,"ble_disabled":true}` |
| `https://<render-url>/docs` | Swagger UI loads |
| `https://<vercel-url>/` | Dashboard loads, STREAMING badge green within 5 s |
| `https://<vercel-url>/digital-twin` | 3D model + PK/PD panel visible |

## Security defaults

- `MEDVERSE_AUTH_ENABLED=false` by default — flip to `true` and set `MEDVERSE_JWT_SECRET` to a strong value to lock down `/api/**` and `/stream`.
- CORS is **not** wildcard. `MEDVERSE_CORS_ORIGINS` defaults to `http://localhost:3000,http://127.0.0.1:3000`. Override for prod.
- The JWT secret has no insecure fallback — production startup hard-fails if auth is enabled without a strong secret set.

## Troubleshooting

- **`/stream` is empty** — check `GET /api/status`. If `using_mock=true` the backend never saw a vest; that's fine for the demo.
- **Frontend can't reach the backend** — set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`.
- **PharmacologyPanel chart is flat** — make sure you clicked **Inject**; the panel only renders effect-curve once `pharmacology.active_medication` is set on the snapshot.

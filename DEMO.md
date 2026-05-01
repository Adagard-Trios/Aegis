# MedVerse — 5-minute demo

## One-command startup

```bash
./start.sh
```

Boots the FastAPI backend on `:8000` and the Next.js frontend on `:3000` in parallel. Ctrl+C tears both down.

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

## Security defaults

- `MEDVERSE_AUTH_ENABLED=false` by default — flip to `true` and set `MEDVERSE_JWT_SECRET` to a strong value to lock down `/api/**` and `/stream`.
- CORS is **not** wildcard. `MEDVERSE_CORS_ORIGINS` defaults to `http://localhost:3000,http://127.0.0.1:3000`. Override for prod.
- The JWT secret has no insecure fallback — production startup hard-fails if auth is enabled without a strong secret set.

## Troubleshooting

- **`/stream` is empty** — check `GET /api/status`. If `using_mock=true` the backend never saw a vest; that's fine for the demo.
- **Frontend can't reach the backend** — set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`.
- **PharmacologyPanel chart is flat** — make sure you clicked **Inject**; the panel only renders effect-curve once `pharmacology.active_medication` is set on the snapshot.

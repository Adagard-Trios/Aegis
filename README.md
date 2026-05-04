# MedVerse

> A multi-specialty clinical telemetry platform that streams live biometric data from a wearable vest and a maternal-fetal monitor, interprets it with a swarm of specialty AI agents, and surfaces the results through a web dashboard, a mobile app, and a 3D digital twin.

MedVerse combines custom ESP32 hardware, a FastAPI + LangGraph backend, a Groq-powered multi-agent LLM layer, a Chroma-backed RAG memory, a Next.js web dashboard, and a Flutter cross-platform app into one system.

---

## Table of Contents

- [What it is](#what-it-is)
- [Key features](#key-features)
- [Workflow diagrams](#workflow-diagrams)
- [System architecture](#system-architecture)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Environment variables](#environment-variables)
- [HTTP / SSE API reference](#http--sse-api-reference)
- [Authentication](#authentication)
- [FHIR R4 interoperability](#fhir-r4-interoperability)
- [Telemetry snapshot schema](#telemetry-snapshot-schema)
- [IMU-derived biomarkers](#imu-derived-biomarkers)
- [Persistence](#persistence)
- [TimescaleDB migration](#timescaledb-migration)
- [LangGraph topology](#langgraph-topology)
- [Expert AI agents](#expert-ai-agents)
- [ML model adapters](#ml-model-adapters)
- [Federated learning](#federated-learning)
- [ECG biometric identity](#ecg-biometric-identity)
- [Sensor channel reference](#sensor-channel-reference)
- [Simulation & PK/PD modeling](#simulation--pkpd-modeling)
- [Web dashboard (frontend/)](#web-dashboard-frontend)
- [Mobile app (mobile/aegis)](#mobile-app-mobileaegis)
- [Firmware (PlatformIO/)](#firmware-platformio)
- [Firmware sample-rate architecture](#firmware-sample-rate-architecture)
- [ML pipelines (models/)](#ml-pipelines-models)
- [Development notes](#development-notes)
- [Troubleshooting](#troubleshooting)
- [Security notice](#security-notice)
- [Roadmap](#roadmap)
- [License](#license)

---

## What it is

MedVerse is an end-to-end telemedicine platform built around two custom wearables — the **Aegis Vest** (ESP32-S3) and the **AbdomenMonitor** (ESP32) — streaming biomedical signals at 40 Hz over BLE to a FastAPI backend. The backend buffers the signals, derives clinical metrics (HR, HRV, SpO₂, breathing rate, perfusion index, posture, fetal kicks, contractions, etc.), persists snapshots to SQLite, and feeds them into a LangGraph multi-agent workflow of specialty experts (cardiology, pulmonary, neurology, dermatology, gynecology/obstetrics, ocular, general physician). Each expert is grounded in a clinical knowledge markdown file and a Chroma-backed RAG memory, and emits a structured JSON assessment (finding / severity / severity score / recommendations / confidence).

The same telemetry stream drives a Next.js 16 dashboard — with a 3D React-Three-Fiber digital twin, per-specialty views, and voice-enabled expert chat — and a Flutter app that runs on Android, iOS, Web, Windows, macOS and Linux.

## Key features

- **Live 10 Hz SSE telemetry** from 30+ sensor channels.
- **Dual BLE devices** — Aegis vest (PPG × 3 sites, 3-lead ECG, 3 skin-temp probes, dual-IMU, BMP280/DHT11, I²S acoustic) and AbdomenMonitor (piezo ×4, MEMS mic, flex film for contractions, ADS1115 16-bit ADC).
- **Graceful mock-data fallback** when no BLE device is present — every part of the stack runs without hardware.
- **Nine-node LangGraph workflow** with patient and doctor orchestrators and 7 parallel specialty sub-graphs, generated from a shared [graph_factory.py](src/graphs/graph_factory.py).
- **Groq-hosted LLM** inference (`openai/gpt-oss-120b`) with per-specialty API key overrides.
- **Biomedical RAG** — Chroma-backed history per specialty, defaults to the `FremyCompany/BioLORD-2023` biomedical encoder with automatic fallback to `all-MiniLM-L6-v2`.
- **Two-compartment PK/PD simulation** — labetalol and oxytocin modeled with a Bateman curve (rise → peak → elimination), CYP2D6-aware clearance, bootstrapped from an OCR pass over uploaded lab-result images (Groq `llama-3.2-11b-vision-preview`).
- **FHIR R4 interoperability** — telemetry serialized as LOINC-coded `Observation` / `Bundle` resources, expert findings as `DiagnosticReport` resources — drop-in compatible with hospital EMRs.
- **Feature-flagged JWT auth** + environment-driven CORS allowlist; enable without changing frontend ports.
- **IMU-derived clinical biomarkers** — tremor-band FFT, gait symmetry, POTS detection, activity classification — all from sensors already on the vest.
- **ML adapter scaffolding** — ECGFounder (10.7M-ECG foundation model), ICBHI respiratory-sound CNN, ECG-biometric Siamese network — plug in weights and the cardiology/pulmonary graphs upgrade from "LLM-only" to structured-model-grounded.
- **Federated learning skeleton** (Flower) — train across patients without their raw biometrics ever leaving their device.
- **TimescaleDB-ready migration** (`alembic upgrade head`) — hypertables + continuous aggregates for the `/history` route.
- **Temporal "what-if" scrubbing** — switch the stream between `Live`, `6h`, `12h`, `24h`, `2w`, `4w` projections.
- **3D digital twin** — GLTF human avatar that reacts in real time to HR, temp, posture, uterine contractions, and fetal kicks.
- **Voice-enabled expert chat** — Web Speech API STT/TTS with markdown-streamed answers.

## Workflow diagrams

The orchestration flow is documented as two PNGs under [assets/](assets/):

![Patient workflow](assets/patient-workflow-updated-4.png)

![Doctor workflow](assets/doctor-workflow-updated-4.png)

## System architecture

```
 ┌─────────────────────┐       ┌──────────────────────┐
 │  Aegis Vest         │       │  AbdomenMonitor      │
 │  ESP32-S3           │       │  ESP32-Dev           │
 │  PPG×3, ECG, IMU×2, │       │  Piezo×4, MEMS mic,  │
 │  DS18B20×3, BMP280, │       │  flex film, ADS1115  │
 │  DHT11, I²S audio   │       │                      │
 └──────────┬──────────┘       └──────────┬───────────┘
            │  BLE (NimBLE)               │  BLE
            │  Aegis_SpO2_Live            │  AbdomenMonitor
            │  char beb5483e-…            │  char 12345678-…
            └──────────────┬──────────────┘
                           ▼
            ┌─────────────────────────────────────┐
            │   FastAPI backend (app.py, :8000)   │
            │   • Env-driven sample rate          │
            │     (BUFFER_SIZE = rate × 20 s)     │
            │   • scipy.signal DSP                │
            │   • IMU biomarkers (tremor, gait,   │
            │     POTS, activity state)           │
            │   • Dawes-Redman CTG (30-min ring)  │
            │   • CORS allowlist (env-driven)     │
            │   • JWT bearer auth (opt-in)        │
            │   • FHIR R4 Observation/Bundle/DR   │
            │   • Mock generator fallback         │
            └────┬───────────────────────────┬────┘
                 │                           │ 1 Hz writer
                 │ SSE 10 Hz + REST          │  (patient_id-keyed)
                 ▼                           ▼
    ┌─────────────────────┐   ┌──────────────────────────────────┐
    │ Next.js dash :3000  │   │ Persistence layer (src/utils/db) │
    │ • /login JWT flow   │   │ • SQLite (default)               │
    │ • /history recharts │   │   — aegis_local.db               │
    │ • 3D twin + chat    │   │ • PostgreSQL + TimescaleDB       │
    │ • NEXT_PUBLIC_API   │   │   when MEDVERSE_DB_URL is set    │
    └─────────────────────┘   │   (hypertables + 1m/1h CAggs)    │
                 │            └──────────────────────────────────┘
                 │
                 │ SSE / REST + Bearer
                 ▼
    ┌─────────────────────┐
    │ Flutter app         │
    │ • Login gate        │
    │ • flutter_secure_   │
    │   storage JWT       │
    │ • ApiConfig over-   │
    │   ridable baseUrl   │
    └─────────────────────┘

     ┌───────────────── LangGraph multi-agent layer ─────────────────┐
     │  patient_graph ── orchestrator ── fan-out                     │
     │            ├── cardiology_graph    ──┐                        │
     │            ├── pulmonary_graph     ──┤                        │
     │            ├── neurology_graph     ──┤                        │
     │            ├── dermatology_graph   ──┼─▶ general_physician    │
     │            ├── gynecology_graph    ──┤     (synthesis)        │
     │            └── ocular_graph        ──┘                        │
     │  doctor_graph ── clinical-staff variant                       │
     │  Each expert → Groq LLM + src/knowledge/*.md + Chroma RAG     │
     └───────────────────────────────────────────────────────────────┘
```

## Repository layout

```
medverse/
├── app.py                    # FastAPI backend — BLE, SSE, REST, DSP, PK/PD, OCR
├── main.py                   # Minimal aux entry
├── train_all.py              # Runner — invokes every models/<slug>/main.py with per-pipeline timeouts + result JSON
├── pipeline_utils.py         # Shared dataset-loader helpers (PhysioNet, Kaggle, HF, Synapse) + DatasetUnavailable
├── start.sh                  # One-command demo (boots backend + frontend)
├── DEMO.md                   # 5-minute demo walkthrough + endpoint reference
├── LICENSE                   # MIT
├── langgraph.json            # Registers 9 LangGraph graphs
├── pyproject.toml            # Python deps (requires-python >=3.13)
├── requirements.txt          # pip-compatible dep list
├── uv.lock                   # uv resolver lockfile
├── .python-version           # 3.13
├── .env                      # Groq + ML pipeline credentials (see SECURITY notice)
├── aegis_local.db            # SQLite telemetry + interpretations (~100 MB, gitignored)
├── train_all_results.json    # Per-pipeline status (ok/gated/timeout/fail), written by train_all.py
├── chroma_data/              # Chroma vector store, one collection per specialty
├── .langgraph_api/           # LangGraph CLI checkpoint pickles
├── assets/                   # Workflow diagram PNGs
├── src/
│   ├── graphs/               # 9 LangGraph definitions + graph_factory.py
│   ├── nodes/                # Graph node implementations
│   ├── states/               # Typed workflow state (patient/doctor/expert)
│   ├── llms/                 # Groq client wrappers
│   ├── knowledge/            # 7 specialty clinical reference .md files
│   ├── utils/                # db.py, fhir.py, auth.py, imu_features.py, …
│   ├── ml/                   # ECGFounder / respiratory-CNN runtime adapters
│   ├── biometric/            # ECG-biometric Siamese identity module
│   ├── federated/            # Flower federated-learning client + server
│   └── exception/            # Error types
├── alembic/                  # TimescaleDB migration (hypertables + aggregates)
│   └── versions/
│       └── 001_timescale_init.py
├── alembic.ini
├── .env.example              # Full env-var reference (safe to commit)
├── frontend/                 # Next.js 16 dashboard (React 19 + Three.js)
├── mobile/aegis/             # Flutter cross-platform client
├── PlatformIO/
│   ├── vest/                 # ESP32-S3 vest firmware + WIRING.md
│   └── fetal_monitor/        # ESP32-Dev abdomen/fetal firmware
└── models/                   # 12 self-contained ML pipelines (one per clinical model)
    ├── README.md             # canonical structure + per-pipeline index
    ├── registry.py           # programmatic pipeline registry
    ├── ecg_arrhythmia/       # cardiology — classification
    ├── cardiac_age/          # cardiology — regression
    ├── ecg_biometric/        # cardiology — metric learning (Siamese)
    ├── stress_ans/           # autonomic — classification
    ├── lung_sound/           # pulmonary — classification
    ├── parkinson_screener/   # neurology — classification
    ├── fetal_health/         # obstetrics — classification
    ├── preterm_labour/       # obstetrics — classification
    ├── bowel_motility/       # GI — classification
    ├── skin_disease/         # dermatology — classification
    ├── retinal_disease/      # ocular — classification
    └── retinal_age/          # ocular — regression
```

## Prerequisites

| Component  | Requirement                                                        |
|------------|--------------------------------------------------------------------|
| Backend    | **Python 3.13** (per [.python-version](.python-version) and [pyproject.toml](pyproject.toml)) |
| Frontend   | **Node 20+**, npm                                                  |
| Mobile     | **Flutter ≥ 3.11**, Dart SDK ^3.11.0 (per [mobile/aegis/pubspec.yaml](mobile/aegis/pubspec.yaml)) |
| Firmware   | **PlatformIO CLI** (`pio`) or the VS Code PlatformIO extension     |
| LLM        | A **Groq API key** (https://console.groq.com)                      |
| OS         | Windows / macOS / Linux. BLE hardware optional (mock fallback)     |

## Quick start

### One-command demo

```bash
./start.sh
```

Boots the FastAPI backend on `:8000` and the Next.js frontend on `:3000` in parallel; Ctrl+C tears both down. See [DEMO.md](DEMO.md) for the 5-minute demo walkthrough, the full endpoint reference, and the **cloud deployment runbook** (Render + Vercel + Timescale Cloud, ~$7/mo). The steps below are the manual equivalent for local dev.

### 1. Backend

```bash
# Install deps (pip or uv)
pip install -r requirements.txt
# …or:
uv sync

# Copy the example env and fill in your Groq key(s)
cp .env.example .env
# …then edit .env and replace every `gsk_replace_me` with a real key

# Run — binds 0.0.0.0:8000
python app.py
```

Optional install extras:

```bash
# Only if you plan to run src/federated/ (Flower + PyTorch)
pip install "flwr>=1.10" "torch>=2.2"

# Only if you're migrating off SQLite to TimescaleDB
pip install "psycopg2-binary>=2.9"
```

On startup, [app.py](app.py) spawns:
- a BLE thread that scans for `Aegis_SpO2_Live` and `AbdomenMonitor` (10 s timeout) and falls back to a mock generator if neither is found,
- a SQLite writer thread that persists a snapshot every 1 s,
- the FastAPI app with a CORS allowlist driven by `MEDVERSE_CORS_ORIGINS` (defaults to `localhost:3000` + `127.0.0.1:3000` — never wildcard).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev       # http://localhost:3000
# or: npm run build && npm run start
# or: npm run lint
```

The dashboard connects to `http://localhost:8000/stream` via `EventSource` with a 3-second auto-reconnect.

### 3. Mobile app

```bash
cd mobile/aegis
flutter pub get
flutter run          # pick your target (android/ios/web/windows/macos/linux)
```

### 4. Firmware

```bash
# Aegis vest (ESP32-S3)
cd PlatformIO/vest
pio run -t upload
pio device monitor -b 115200

# Abdomen / fetal monitor (ESP32-Dev — pinned to COM3 on Windows)
cd ../fetal_monitor
pio run -t upload
pio device monitor -b 115200
```

See [PlatformIO/vest/WIRING.md](PlatformIO/vest/WIRING.md) for the full pinout.

### 5. LangGraph dev server (optional)

```bash
# Opens LangGraph Studio against langgraph.json
langgraph dev
```

## Environment variables

All variables are loaded from [.env](.env) via `python-dotenv`. A complete, safe-to-commit template lives in [.env.example](.env.example) — copy it to `.env` and fill in the Groq key(s). The backend falls back to the shared `GROQ_API_KEY` when a specialty-specific key is absent.

### Groq LLM keys

| Variable                              | Purpose                                                     |
|---------------------------------------|-------------------------------------------------------------|
| `GROQ_API_KEY`                        | Default Groq key (used by `app.py` OCR + fallback for all experts) |
| `CARDIOLOGY_EXPERT_GROQ_API_KEY`      | Cardiology expert LLM                                       |
| `PULMONARY_EXPERT_GROQ_API_KEY`       | Pulmonary expert LLM                                        |
| `NEUROLOGY_EXPERT_GROQ_API_KEY`       | Neurology expert LLM                                        |
| `DERMATOLOGY_EXPERT_GROQ_API_KEY`     | Dermatology expert LLM                                      |
| `GYNECOLOGY_EXPERT_GROQ_API_KEY`      | Gynecology/obstetrics expert LLM                            |
| `OCULOMETRIC_EXPERT_GROQ_API_KEY`     | Ocular/oculometric expert LLM                               |
| `GENERAL_PHYSICIAN_GROQ_API_KEY`      | Synthesizing general-physician LLM                          |
| `INFECTIOUS_DISEASE_EXPERT_GROQ_API_KEY` | Reserved — infectious-disease expert                     |
| `PSYCHIATRIC_EXPERT_GROQ_API_KEY`     | Reserved — psychiatric expert                               |
| `ENVIRONMENT_EXPERT_GROQ_API_KEY`     | Reserved — environmental-health expert                      |
| `ENT_EXPERT_GROQ_API_KEY`             | Reserved — ENT expert                                       |
| `ORTHOPEDIC_EXPERT_GROQ_API_KEY`      | Reserved — orthopedic expert                                |
| `PHARMACOLOGY_EXPERT_GROQ_API_KEY`    | Reserved — pharmacology expert                              |
| `ENDOCRINOLOGIST_EXPERT_GROQ_API_KEY` | Reserved — endocrinology expert                             |
| `NEPHROLOGY_EXPERT_GROQ_API_KEY`      | Reserved — nephrology expert                                |

### Backend runtime flags

| Variable                          | Default                                               | Purpose |
|-----------------------------------|-------------------------------------------------------|---------|
| `MEDVERSE_SAMPLE_RATE`            | `40`                                                  | Expected BLE payload cadence. Drives `BUFFER_SIZE`, `SPO2_WINDOW`, `BR_WINDOW`. See [Firmware sample-rate architecture](#firmware-sample-rate-architecture) before bumping this past `40` — NimBLE packet rate is the real ceiling, not the env var. |
| `MEDVERSE_AUTH_ENABLED`           | `false`                                               | When `true`, `/api/**` endpoints require a valid JWT bearer token |
| `MEDVERSE_JWT_SECRET`             | *(unset → ephemeral random in dev; required in prod)* | HMAC secret used to sign JWTs. When `MEDVERSE_AUTH_ENABLED=true` and this is missing/weak, startup raises `RuntimeError`. |
| `MEDVERSE_JWT_ALG`                | `HS256`                                               | JWT signing algorithm |
| `MEDVERSE_JWT_EXPIRY_SECONDS`     | `3600`                                                | Access-token lifetime |
| `MEDVERSE_DEV_USERNAME`           | `medverse`                                            | Dev-login username (`POST /api/auth/login`) |
| `MEDVERSE_DEV_PASSWORD`           | `medverse`                                            | Dev-login password |
| `MEDVERSE_CORS_ORIGINS`           | `http://localhost:3000,http://127.0.0.1:3000`         | Comma-separated CORS origin allowlist |
| `MEDVERSE_EMBEDDING_MODEL`        | `FremyCompany/BioLORD-2023`                           | Primary Chroma embedding model (auto-falls back to `all-MiniLM-L6-v2`) |
| `MEDVERSE_INCLUDE_WAVEFORM`       | `false`                                               | When `true`, `/stream` includes the raw 800-sample waveform buffers (needed by the ML adapters) |
| `MEDVERSE_MODELS_DIR`             | `./models`                                            | Root searched by `src/ml/` and `src/biometric/` adapters for weight files |
| `MEDVERSE_BIOMETRIC_THRESHOLD`    | `0.75`                                                | Cosine-similarity threshold for a positive biometric match |
| `MEDVERSE_DB_URL`                 | *(unset)*                                             | Postgres/Timescale connection string. When set, telemetry + interpretation writes go to Postgres and `/api/history` reads from the `telemetry_vitals_*` continuous aggregates. |
| `NEXT_PUBLIC_API_URL`             | `http://localhost:8000`                               | Frontend-side — points the Next.js dashboard at any backend host. See [frontend/.env.example](frontend/.env.example). |

### Federated-learning (optional)

| Variable          | Default         | Purpose                        |
|-------------------|-----------------|--------------------------------|
| `FL_SERVER`       | `127.0.0.1:8080`| FedAvg aggregator address      |
| `FL_PATIENT_ID`   | `default_patient`| Client's patient id           |
| `FL_ROUNDS`       | `10`            | Number of aggregation rounds   |

### ML pipeline data-loading credentials

Loaded by [pipeline_utils.py](pipeline_utils.py) via `python-dotenv` from the same root [.env](.env). Each pipeline's `_load_dataframe` raises `DatasetUnavailable` with a precise hint when a required credential is missing — pipelines that don't need a credential download their data on first run automatically.

| Variable                | Default | Purpose |
|-------------------------|---------|---------|
| `KAGGLE_USERNAME`       | *(unset)* | Kaggle API username — required for `skin_disease`, `retinal_disease`, `retinal_age` (HAM10000 / ODIR-5K) and the ICBHI mirror fallback for `lung_sound`. Get from https://www.kaggle.com/settings/account → "Create New API Token". |
| `KAGGLE_KEY`            | *(unset)* | Kaggle API key (paired with `KAGGLE_USERNAME`). |
| `HF_TOKEN`              | *(unset)* | HuggingFace token — required for `retinal_age` (RETFound MAE weights via `hf_hub_download`). Read scope is enough. |
| `SYNAPSE_AUTH_TOKEN`    | *(unset)* | Synapse access token — required for `parkinson_screener`'s WearGait-PD gait signals. Without it, the pipeline still runs on UCI Parkinsons voice features only. |
| `MEDVERSE_FETCH_LARGE`  | `false` | Opt-in switch for large datasets. When `false`, pipelines that depend on PTB-XL (25 GB), PTB diagnostic ECG (7 GB), CTU-UHB CTG waveforms (500 MB), or ISIC 2024 (~25 GB) raise `DatasetUnavailable` instead of silently downloading. Set to `true` when you actually want the full datasets. |
| `WESAD_ROOT`            | *(unset)* | Optional path to a manually-downloaded WESAD dataset (real WESAD requires email registration at uni-siegen.de). When unset, `stress_ans` falls back to the synthetic generator from the source notebook. |

### Frontend env

Frontend env lives in [frontend/.env.example](frontend/.env.example) — copy to `frontend/.env.local` if you need to point the dashboard at a different backend. The single variable is `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

## HTTP / SSE API reference

All endpoints are defined in [app.py](app.py). Base URL: `http://localhost:8000`. Swagger UI: `http://localhost:8000/docs`.

### Telemetry

| Method | Path                          | Purpose |
|--------|-------------------------------|---------|
| GET    | `/api/status`                 | Device-connection flags, sample rate, packet count |
| GET    | `/stream?token=…&patient_id=…` | **SSE** — 10 Hz telemetry snapshot stream (with simulation-mode + PK/PD overlay). `token` required when `MEDVERSE_AUTH_ENABLED=true` (EventSource can't carry headers). |
| GET    | `/api/snapshot?patient_id=…`  | Latest telemetry row from the active DB backend (falls back to live snapshot) |
| GET    | `/api/interpretations?patient_id=…` | Latest AI interpretation per specialty |
| GET    | `/api/history?resolution=1m\|1h&patient_id=…&limit=500` | Rolled-up HR / SpO₂ / BR / HRV time series — uses Timescale continuous aggregates when `MEDVERSE_DB_URL` is set, otherwise bucketed from SQLite |
| GET    | `/api/patient/active`         | Returns the in-memory `ACTIVE_PATIENT_ID` used by the snapshot writer |
| POST   | `/api/patient/active`         | Body: `{"patient_id": str}` — sets the writer's active patient |

### Simulation

| Method | Path                          | Purpose |
|--------|-------------------------------|---------|
| POST   | `/api/simulation/mode`        | Body: `{"mode": "Live"\|"6h"\|"12h"\|"24h"\|"2w"\|"4w"}` — temporal projection |
| POST   | `/api/simulation/scenario`    | Body: `{"scenario": "normal"\|"tachycardia"\|"hypoxia"\|"fetal_decel"\|"arrhythmia"}` — switches the live mock-data scenario to drive agent fan-out |
| GET    | `/api/simulation/scenario`    | Returns `{"scenario": str, "available": [str]}` |
| POST   | `/api/simulation/medicate`    | Body: `{"medication": str, "dose": float}` — starts a Bateman PK/PD curve |
| POST   | `/api/simulation/cyp2d6`      | Body: `{"status": "Normal Metabolizer"\|"Poor Metabolizer"}` — toggles k_el modulation in the PK/PD overlay |
| POST   | `/api/upload-lab-results`     | Multipart `file` (PNG/JPG lab report) — extracts AST/ALT/CYP2D6 via Groq vision and sets `PATIENT_CYP2D6_STATUS` |

### Authentication

| Method | Path                          | Purpose |
|--------|-------------------------------|---------|
| POST   | `/api/auth/login`             | Body: `{"username": str, "password": str}` → `{"access_token": "...", "token_type": "bearer"}` |
| GET    | `/api/auth/me`                | Returns the decoded JWT payload (or `{"sub":"anonymous"}` when auth is disabled) |

### FHIR R4 interop

| Method | Path                                          | Purpose |
|--------|-----------------------------------------------|---------|
| GET    | `/api/fhir/Observation/latest`                | Latest snapshot as a list of LOINC-coded `Observation` resources |
| GET    | `/api/fhir/Bundle/latest`                     | Same, wrapped in a `Bundle` of `type: collection` |
| GET    | `/api/fhir/DiagnosticReport/latest`           | All specialty interpretations as `DiagnosticReport` resources |
| GET    | `/api/fhir/DiagnosticReport/{specialty}/latest` | Single specialty's latest `DiagnosticReport` |
| GET    | `/api/fhir/Patient/{patient_id}`              | Minimal `Patient` resource |
| GET    | `/api/fhir/Device`                            | `Device` resources for the vest and abdomen monitor |

All FHIR routes accept an optional `?patient_id=...` query parameter (default `medverse-demo-patient`) and are gated by `Depends(require_user)` — anonymous-passthrough while `MEDVERSE_AUTH_ENABLED=false`.

### Stream payload

The SSE `data:` field is a JSON object shaped like the telemetry snapshot in the next section.

## Telemetry snapshot schema

Built by `build_telemetry_snapshot()` in [app.py](app.py). Emitted on `/stream` at 10 Hz and persisted to SQLite at 1 Hz.

```jsonc
{
  "timestamp": 12345,
  "ppg":        { "ir1", "red1", "ir2", "red2", "ira", "reda", "t1", "t2" },
  "temperature":{ "left_axilla", "right_axilla", "cervical" },
  "imu":        { "upper_pitch", "upper_roll", "lower_pitch", "lower_roll",
                  "spinal_angle", "poor_posture", "posture_label",
                  "bmp180_pressure", "bmp180_temp" },
  "environment":{ "bmp280_pressure", "bmp280_temp",
                  "dht11_humidity", "dht11_temp" },
  "ecg":        { "lead1", "lead2", "lead3", "ecg_hr" },
  "audio":      { "analog_rms", "digital_rms" },
  "vitals":     { "heart_rate", "spo2", "breathing_rate",
                  "hrv_rmssd", "perfusion_index", "signal_quality" },
  "connection": { "vest_connected", "fetal_connected", "using_mock" },
  "fetal":      { "mode", "piezo_raw[4]", "kicks[4]", "movement[4]",
                  "mic_volts[2]", "heart_tones[2]", "bowel_sounds[2]",
                  "film_pressure[2]", "contractions[2]" },
  "pharmacology":{ "active_medication", "dose", "sim_time",
                   "clearance_model", "effect_curve", "k_el" },
  "scenario":   "normal|tachycardia|hypoxia|fetal_decel|arrhythmia",
  "imu_derived": {
    "tremor":   { "band_power", "total_power", "band_ratio", "tremor_flag" },
    "gait":     { "stride_count", "mean_stride_s", "stride_cv", "asymmetry_flag" },
    "pots":     { "hr_jump", "angle_delta", "pots_flag" },
    "activity_state": "rest|walking|running|unknown"
  },
  "waveform":   null  // or, when MEDVERSE_INCLUDE_WAVEFORM=true:
                      // { "fs", "ecg_lead1[800]", "ecg_lead2[800]", "ecg_lead3[800]",
                      //   "ppg_ira[800]", "ppg_reda[800]", "audio[800]" }
}
```

Derived vitals are produced with `scipy.signal`:
- **HR / HRV (RMSSD)** — band-pass 0.5–4 Hz on IRA PPG, then `find_peaks` with a 180-bpm-max refractory window ([app.py:160](app.py#L160)).
- **SpO₂** — AC/DC ratio of RedA/IRA against a 30-entry lookup table ([app.py:139](app.py#L139)).
- **Breathing rate** — 0.5 Hz low-pass on IR1 over a 10-s window ([app.py:187](app.py#L187)).
- **Perfusion index** — `std(IRA) / mean(IRA) × 100` ([app.py:200](app.py#L200)).
- **Signal quality** — discretized `Excellent / Good / Fair / Poor / No contact` from PI.
- **Posture label** — spinal-angle magnitude thresholds (5° / 15°).

## Authentication

Implemented in [src/utils/auth.py](src/utils/auth.py). Off by default so the existing frontend keeps working; flip on with a single env var.

```bash
# Enable
MEDVERSE_AUTH_ENABLED=true \
MEDVERSE_JWT_SECRET=<long-random-string> \
python app.py

# Log in (dev credentials in .env.example: medverse/medverse)
curl -X POST http://localhost:8000/api/auth/login \
  -H 'content-type: application/json' \
  -d '{"username":"medverse","password":"medverse"}'
# → {"access_token":"eyJ...","token_type":"bearer","auth_enabled":true}

# Call a protected endpoint
curl http://localhost:8000/api/fhir/Observation/latest \
  -H 'authorization: Bearer eyJ...'
```

Signing algorithm and token lifetime are env-configurable (`MEDVERSE_JWT_ALG`, `MEDVERSE_JWT_EXPIRY_SECONDS`). All `/api/fhir/**` endpoints use `Depends(require_user)` — they pass an anonymous principal through when auth is disabled, and 401 with `WWW-Authenticate: Bearer` when it is enabled and no/invalid token is sent.

### CORS

Driven by `MEDVERSE_CORS_ORIGINS` — a comma-separated allowlist. Default covers both `localhost:3000` and `127.0.0.1:3000` so the Next.js dev server works without extra configuration.

## FHIR R4 interoperability

Implemented in [src/utils/fhir.py](src/utils/fhir.py). Serializers emit plain dicts conforming to the FHIR R4 JSON shape; if the optional `fhir.resources` package is installed, outputs are additionally validated against the official Pydantic models.

### Observation coding

| Telemetry field              | LOINC code | Display                    | Unit    |
|------------------------------|------------|----------------------------|---------|
| `vitals.heart_rate`          | `8867-4`   | Heart rate                 | `/min`  |
| `vitals.spo2`                | `59408-5`  | Oxygen saturation          | `%`     |
| `vitals.breathing_rate`      | `9279-1`   | Respiratory rate           | `/min`  |
| `vitals.hrv_rmssd`           | `80404-7`  | R-R interval SDNN          | `ms`    |
| `vitals.perfusion_index`     | `61006-3`  | Perfusion index            | `%`     |
| `temperature.cervical`       | `8310-5`   | Body temperature           | `Cel`   |
| `temperature.left_axilla`    | `8328-7`   | Axillary temp (left)       | `Cel`   |
| `temperature.right_axilla`   | `8328-7`   | Axillary temp (right)      | `Cel`   |
| `imu.spinal_angle`           | `41950-7`  | Posture angle              | `deg`   |
| `fetal.contractions`         | `82310-5`  | Uterine contraction count  | `{count}` |

### DiagnosticReport coding

| Specialty            | LOINC code | Display                 |
|----------------------|------------|-------------------------|
| Cardiology           | `18753-8`  | Cardiology study        |
| Pulmonary            | `18748-8`  | Pulmonology study       |
| Neurology            | `47043-1`  | Neurology consultation  |
| Dermatology          | `34111-5`  | Dermatology report      |
| Gynecology           | `47040-7`  | Obstetrics consultation |
| Ocular               | `29271-4`  | Ophthalmology report    |
| General physician    | `11488-4`  | Consultation note       |

Each `DiagnosticReport` carries three MedVerse extensions: `severity` (`valueString`), `severity-score` (`valueDecimal`), `ai-confidence` (`valueDecimal`).

### Example

```bash
curl http://localhost:8000/api/fhir/Bundle/latest?patient_id=patient-042 | jq
```

```jsonc
{
  "resourceType": "Bundle",
  "type": "collection",
  "timestamp": "2026-04-19T14:22:33.512Z",
  "entry": [
    { "resource": { "resourceType": "Observation", "code": { "coding": [{ "system": "http://loinc.org", "code": "8867-4" }] }, "valueQuantity": { "value": 78.0, "unit": "/min" }, "...": "..." } },
    { "resource": { "resourceType": "Observation", "code": { "coding": [{ "system": "http://loinc.org", "code": "59408-5" }] }, "valueQuantity": { "value": 97.0, "unit": "%" }, "...": "..." } }
  ]
}
```

## Dawes-Redman CTG surrogate

Maternal-fetal CTG (cardiotocography) analysis runs out-of-band from the 800-sample telemetry buffers — proper Dawes-Redman criteria require a 10-minute FHR trace. [src/utils/ctg_dawes_redman.py](src/utils/ctg_dawes_redman.py) maintains a 30-minute, 1 Hz ring buffer seeded from every snapshot and attaches its latest assessment at `fetal.dawes_redman`:

```jsonc
"dawes_redman": {
  "samples":          1234,      // seconds accumulated
  "analysis_ready":   true,      // ≥ 10 min of data
  "baseline_fhr":     142.3,     // bpm, trimmed mean
  "stv_ms":           4.8,       // short-term variation
  "accelerations":    3,         // ≥15 bpm rises held ≥15 s
  "decelerations":    0,
  "criteria_met":     true       // baseline 110-160, stv ≥ 3 ms, ≥1 accel, no decels
}
```

When the AbdomenMonitor piezo stream is absent the analyzer falls back to a maternal-HR-offset FHR estimate (maternal + 65 bpm, clipped to 110-165) so demos without fetal hardware still populate the dashboard. This is a **screening surrogate**, not the full commercial Sonicaid algorithm — it captures baseline, STV, accels and decels, and the composite criteria gate.

## IMU-derived biomarkers

Computed in [src/utils/imu_features.py](src/utils/imu_features.py) from the two MPU6050 IMU streams already on the vest — no hardware changes, no sampling-rate changes. Appended to every telemetry snapshot under `imu_derived`.

| Biomarker                  | Method | Flag condition | Clinical relevance |
|----------------------------|--------|----------------|--------------------|
| `tremor.band_power`        | Welch PSD of combined upper IMU, integrated over 4–8 Hz | `band_ratio > 0.25` and `band_power > 0.01` | Parkinson's resting tremor band |
| `gait.stride_cv`           | Coefficient of variation of stride intervals from lower-IMU pitch peaks | `stride_cv > 0.10` | Validated fall-risk marker |
| `pots.pots_flag`           | HR jump within 30 s of posture-angle change | `hr_jump > 30 bpm` **and** `|angle_delta| > 20°` | Postural orthostatic tachycardia |
| `activity_state`           | IMU magnitude variance thresholds (rest/walking/running) | — | Context-aware vital normalization |

All functions are tolerant of short or empty buffers (return zeros + `False` flags) so the 10 Hz SSE loop never blocks on a DSP edge case.

## Persistence

| Store                      | Location                  | What it holds |
|----------------------------|---------------------------|---------------|
| SQLite (default)           | [aegis_local.db](aegis_local.db) | `telemetry(id, timestamp_str, patient_id, data JSON)` and `interpretations(id, timestamp_str, patient_id, specialty, findings, severity, severity_score)`. Written at 1 Hz under `ACTIVE_PATIENT_ID` by `sqlite_writer_loop`. Indexed on `(patient_id, id DESC)`. |
| PostgreSQL + TimescaleDB   | Postgres at `MEDVERSE_DB_URL` | Hypertables with the same columns (`ts TIMESTAMPTZ`, `data JSONB`), plus `telemetry_vitals_1m` / `telemetry_vitals_1h` continuous aggregates and a 30-day retention policy. [src/utils/db.py](src/utils/db.py) routes reads/writes here automatically when the env var is set. |
| Chroma vector store        | [chroma_data/](chroma_data/) | One collection per specialty (e.g. `cardiology_history`). Embeddings: HuggingFace `BioLORD-2023` (default) or `all-MiniLM-L6-v2` (fallback). |
| LangGraph checkpoints      | [.langgraph_api/](.langgraph_api/) | `.langgraph_checkpoint.*.pckl`, `.langgraph_ops.pckl`, `store.*` — in-memory store snapshots persisted by `langgraph dev`. |

## TimescaleDB migration

SQLite ([aegis_local.db](aegis_local.db)) is the default and requires no setup. A drop-in PostgreSQL + TimescaleDB migration is staged under [alembic/](alembic/) for when the data volume outgrows SQLite's JSON-blob scans.

```bash
# One-time: create the DB + enable the extension on your Postgres server
createdb medverse
psql medverse -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# Apply
export MEDVERSE_DB_URL=postgresql+asyncpg://medverse:<pw>@localhost:5432/medverse
alembic upgrade head
```

The migration at [alembic/versions/001_timescale_init.py](alembic/versions/001_timescale_init.py) creates:

- **`telemetry`** hypertable — `id`, `patient_id`, `ts`, `data JSONB`, GIN index on `data`, composite index on `(patient_id, ts DESC)`.
- **`interpretations`** hypertable — specialty + severity + severity_score, indexed on `(patient_id, specialty, ts DESC)`.
- **`telemetry_vitals_1m`** continuous aggregate — 1-minute averages of HR / SpO₂ / BR / HRV.
- **`telemetry_vitals_1h`** continuous aggregate — 1-hour averages.
- 30-day retention policy on raw telemetry (aggregates keep forever).

The FastAPI backend still reads/writes SQLite until you switch the writer loop in [src/utils/db.py](src/utils/db.py) — the migration is a ready-to-apply artifact, not an in-place replacement.

## LangGraph topology

Registered in [langgraph.json](langgraph.json):

| Graph id                   | Source                                                          | Role |
|----------------------------|-----------------------------------------------------------------|------|
| `patient_graph`            | [src/graphs/patient_graph.py](src/graphs/patient_graph.py)      | Patient-facing orchestrator — init → parallel (monitoring, expert swarm) → audience-aware compiler |
| `doctor_graph`             | [src/graphs/doctor_graph.py](src/graphs/doctor_graph.py)        | Clinician-facing orchestrator with NFC/records integration and critical-alert prioritization |
| `cardiology_graph`         | [src/graphs/cardiology_graph.py](src/graphs/cardiology_graph.py) | ECG/PPG-driven cardiac assessment |
| `pulmonary_graph`          | [src/graphs/pulmonary_graph.py](src/graphs/pulmonary_graph.py)  | SpO₂, breathing, lung-sound assessment |
| `neurology_graph`          | [src/graphs/neurology_graph.py](src/graphs/neurology_graph.py)  | IMU-derived gait, tremor, fall-risk, autonomic HRV |
| `dermatology_graph`        | [src/graphs/dermatology_graph.py](src/graphs/dermatology_graph.py) | Skin-temp gradient, sweat profile |
| `gynecology_graph`         | [src/graphs/gynecology_graph.py](src/graphs/gynecology_graph.py) | Maternal-fetal: FHR, contractions, kicks, Dawes-Redman |
| `ocular_graph`             | [src/graphs/ocular_graph.py](src/graphs/ocular_graph.py)        | Ocular / oculometric surrogate |
| `general_physician_graph`  | [src/graphs/general_physician_graph.py](src/graphs/general_physician_graph.py) | Synthesizer — combines specialist outputs into a unified narrative |

The specialty sub-graphs share a common `information_retrieval → interpretation_generation` skeleton produced by [src/graphs/graph_factory.py](src/graphs/graph_factory.py), using the state shapes defined under [src/states/](src/states/).

## Expert AI agents

Each specialty expert loads: a clinical knowledge base from [src/knowledge/](src/knowledge/), the current telemetry snapshot, prior-session retrieval from Chroma, and the patient profile. It then calls Groq (`openai/gpt-oss-120b`, temperature 0.3) and emits a Pydantic-validated JSON response.

| Specialty           | Knowledge file                                                  | Env-var override                        |
|---------------------|------------------------------------------------------------------|-----------------------------------------|
| Cardiology          | [src/knowledge/cardiology.md](src/knowledge/cardiology.md)       | `CARDIOLOGY_EXPERT_GROQ_API_KEY`        |
| Pulmonary           | [src/knowledge/pulmonary.md](src/knowledge/pulmonary.md)         | `PULMONARY_EXPERT_GROQ_API_KEY`         |
| Neurology           | [src/knowledge/neurology.md](src/knowledge/neurology.md)         | `NEUROLOGY_EXPERT_GROQ_API_KEY`         |
| Dermatology         | [src/knowledge/dermatology.md](src/knowledge/dermatology.md)     | `DERMATOLOGY_EXPERT_GROQ_API_KEY`       |
| Gynecology          | [src/knowledge/gynecology.md](src/knowledge/gynecology.md)       | `GYNECOLOGY_EXPERT_GROQ_API_KEY`        |
| Ocular              | [src/knowledge/ocular.md](src/knowledge/ocular.md)               | `OCULOMETRIC_EXPERT_GROQ_API_KEY`       |
| General Physician   | [src/knowledge/general_physician.md](src/knowledge/general_physician.md) | `GENERAL_PHYSICIAN_GROQ_API_KEY` |

### Structured output schema

```jsonc
{
  "finding":         "string (≥ 300 chars — enforced)",
  "severity":        "normal | watch | elevated | critical",
  "severity_score":  0.0,   // 0–10 float
                            //  0–2 normal, 3–4 watch, 5–7 elevated, 8–10 critical
  "recommendations": ["string", "..."],
  "confidence":      0.0    // 0–1
}
```

## ML model adapters

Runtime wrappers under [src/ml/](src/ml/) let the cardiology and pulmonary LangGraph nodes **narrate** structured model output instead of classifying from text alone. Every adapter is a singleton with a uniform `is_loaded` / `classify` / `embed` surface, and every adapter gracefully no-ops when weights are absent — the graphs keep running either way.

| Adapter                                                                          | Weights path (relative to `MEDVERSE_MODELS_DIR`) | Graph integration point |
|----------------------------------------------------------------------------------|--------------------------------------------------|-------------------------|
| [`ECGFounderAdapter`](src/ml/ecgfounder_adapter.py)                              | `ecg/ecgfounder/weights.pt` + `labels.txt`       | `cardiology_graph` info-retrieval |
| [`RespiratorySoundClassifier`](src/ml/pulmonary_classifier.py)                   | `pulmonary/icbhi_cnn/weights.pt` + `class_names.json` | `pulmonary_graph` info-retrieval |
| [`ECGBiometric`](src/biometric/ecg_biometric.py)                                 | `ecg/biometric_siamese/weights.pt`               | (see [ECG biometric identity](#ecg-biometric-identity)) |

### How graphs consume adapter output

`_augment_with_ml_models()` in [src/graphs/graph_factory.py](src/graphs/graph_factory.py) runs after the normal tool pass. When the adapter is loaded **and** the snapshot carries a `waveform` block (enable with `MEDVERSE_INCLUDE_WAVEFORM=true`), it attaches a structured result to `tool_results`:

```jsonc
// tool_results entry from the cardiology graph
"ecgfounder_classification": {
  "label": "Atrial Fibrillation",
  "auroc": 0.97,
  "top_k": [{"label": "AF", "prob": 0.91}, ...]
}
```

The LLM then narrates this structured classification rather than inferring it from raw signal — a triply-sourced output (signal → classifier → LLM narration) that is clinically defensible.

### Plugging in weights

Each adapter file contains a `_load_weights()` method with a `NotImplementedError` — drop in your PyTorch / TFLite / ONNX load call there, or override the singleton at runtime. See the inline docstrings for the expected I/O shape (1-D ECG window, mel-spectrogram audio window, Siamese anchor embedding).

## Federated learning

Scaffolding under [src/federated/](src/federated/) lets you train shared models across patients while each device's `aegis_local.db` (raw biometrics) **never leaves the device** — only gradient deltas are uploaded.

```bash
# Install the optional stack
pip install "flwr>=1.10" "torch>=2.2"

# On the coordinator host
python -m src.federated.server --rounds 10 --address 0.0.0.0:8080

# On each participating device
python -m src.federated.client --server-address 10.0.0.4:8080 --patient-id patient_042
```

- Server uses `FedAvg` with `min_fit_clients=2`, `min_available_clients=2`.
- Client defines a `TinyArrhythmiaModel` placeholder (`nn.Linear`-based) — swap for your production CNN in [src/federated/client.py](src/federated/client.py).
- `load_local_training_set(patient_id)` is a stub — wire it to pull labelled ECG windows from the local SQLite.

## ECG biometric identity

Implemented in [src/biometric/ecg_biometric.py](src/biometric/ecg_biometric.py). A Siamese encoder learns each patient's unique cardiac morphology; stored anchor embeddings (persisted in the existing `cardiology_history` Chroma collection under `metadata.type = "biometric_anchor"`) enable:

- **Passive session identification** — the vest recognises the wearer from their ECG, no login step.
- **Personalised drift monitoring** — deviation from the patient's *own* baseline triggers alerts, not just absolute thresholds.
- **Cross-patient session hygiene** — if a different person puts on the vest, the biometric mismatch is flagged.

API:

```python
from src.biometric.ecg_biometric import get_ecg_biometric

bio = get_ecg_biometric()
if bio.is_loaded:
    anchor = bio.enroll(patient_id="patient_042", ecg_windows=[...])  # persist anchor
    match = bio.identify(ecg_window=current, anchors=[("patient_042", anchor)])
    # match.matched == match.score >= MEDVERSE_BIOMETRIC_THRESHOLD (default 0.75)
```

Until weights land under `models/ecg/biometric_siamese/weights.pt`, `is_loaded` stays `False` and all public methods return safe sentinels.

## Sensor channel reference

Channels appear in the BLE payload as comma-separated `key:value` pairs and are parsed at [app.py:252](app.py#L252).

| Group     | Keys                                          | Source sensor |
|-----------|-----------------------------------------------|---------------|
| PPG       | `IR1`, `Red1`, `IR2`, `Red2`, `IRA`, `RedA`   | MAX30102 × 3 sites |
| PPG temps | `T1`, `T2`                                    | MAX30102 on-board |
| Skin temp | `TL`, `TR`, `TC`                              | DS18B20 × 3 (L axilla, R axilla, cervical) |
| IMU       | `UP`, `UR`, `LP`, `LR`, `SA`, `PP`            | MPU6050 × 2 (upper/lower pitch/roll + spinal angle + poor-posture flag) |
| GY-87     | `BPR`, `BTP`                                  | BMP180 pressure / temperature |
| Env       | `EP`, `ET`, `HUM`, `DT`                       | BMP280 + DHT11 |
| ECG       | `L1`, `L2`, `L3`, `EHR`                       | AD8232 3-lead + on-board HR |
| Audio     | `ARMS`, `DRMS`                                | I²S acoustic array (analog + digital RMS) |

Fetal payload is JSON (not key:value) — parsed at [app.py:231](app.py#L231): `mode`, `pz[4]`, `kick[4]`, `move[4]`, `mv[2]`, `heart[2]`, `bowel[2]`, `fp[2]`, `cont[2]`.

## Simulation & PK/PD modeling

### Temporal projection

`POST /api/simulation/mode` shifts the live snapshot into projected futures (see [app.py:692](app.py#L692)):

| Mode   | Effect                                                              |
|--------|---------------------------------------------------------------------|
| `Live` | Pass-through — no modification                                      |
| `6h`   | HR − 10 bpm (min 60), cervical 37 °C, contractions cleared          |
| `12h`  | HR 80, cervical 36.8, single kick                                   |
| `24h`  | HR 72, cervical 36.6, alternating kicks                             |
| `2w`   | Spinal angle + 5°, HR 85                                            |
| `4w`   | Spinal angle + 12°, HR 95, both contractions + 3/4 kicks            |

### Clinical scenarios

`POST /api/simulation/scenario` switches the live mock-data feed into a clinical edge-case so the agent fan-out has something to react to during demos. Layered *underneath* the temporal projection and PK/PD overlays — drug effects still apply on top.

| Scenario       | Effect on snapshot                                                                                  |
|----------------|------------------------------------------------------------------------------------------------------|
| `normal`       | Pass-through (default)                                                                               |
| `tachycardia`  | HR clamped to ~138 bpm with ±3 jitter; `ecg_hr` mirrored; HRV depressed to ~18 ms                    |
| `hypoxia`      | SpO₂ → ~88%, RR → ~24, HR shifted +12 bpm                                                            |
| `fetal_decel`  | Forces both contractions on, suppresses fetal kicks, sets Dawes-Redman to `non-reactive` + `late` decels with `fhr_baseline=95` |
| `arrhythmia`   | HRV spikes to ~95 ms; 15% of ticks add a ±25–30 bpm HR transient                                     |

The active scenario is broadcast on every tick at `snapshot.scenario`. Read it back with `GET /api/simulation/scenario`.

### Drug injection

`POST /api/simulation/medicate` overlays a **two-compartment Bateman** PK/PD curve on the stream. The effect rises from zero, peaks, then decays — so the simulation actually washes out instead of locking at max effect.

```
C(t) ∝ (k_abs / (k_abs − k_el)) · (e^−k_el·t − e^−k_abs·t)

Poor CYP2D6 metabolizer → k_el × 0.6   (slower clearance, larger AUC, longer tail)
Normal metabolizer       → k_el × 1.0
```

Per-drug constants (see [app.py](app.py)):

| Drug         | k_abs | k_el (Normal) | HR effect                                              | Contraction effect |
|--------------|-------|---------------|---------------------------------------------------------|--------------------|
| Labetalol    | 0.4   | 0.25          | `−15 × effect × (dose/100)` bpm                         | —                  |
| Oxytocin     | 0.8   | 0.45          | `+5 × effect × (dose/100)` bpm                          | Active when `effect × dose/100 > 0.15` |

`effect` is clipped to `[0, 1]` and exposed in the stream at `pharmacology.effect_curve`; the active `k_el` is at `pharmacology.k_el`. Once `sim_time > 3.0` and `effect_curve < 0.005`, the active medication is cleared automatically so a fresh `/api/simulation/medicate` call gives a clean curve.

### CYP2D6 status

Two paths set `PATIENT_CYP2D6_STATUS`:

1. **Manual toggle** — `POST /api/simulation/cyp2d6` with `{"status": "Normal Metabolizer"|"Poor Metabolizer"}`. Used by the PK/PD panel on `/digital-twin` for live demo flips.
2. **Lab-result OCR** — `POST /api/upload-lab-results` accepts a PNG/JPG of a lab report and calls Groq `llama-3.2-11b-vision-preview` to extract AST, ALT, and CYP2D6 metabolizer status ([app.py:804](app.py#L804)). If CYP2D6 is not explicitly listed, it is deduced from liver enzymes (AST/ALT > 100 U/L ⇒ `Poor Metabolizer`).

The resulting status drives the clearance constant above (`Poor Metabolizer` → `k_el × 0.6`).

## Web dashboard (frontend/)

**Stack** — Next.js 16.1.7 (App Router, client components, Turbopack builds), React 19.2.3, TypeScript 5, Tailwind CSS 4, Framer Motion 12, **Lenis** smooth-scroll for the parallax landing page, lucide-react, react-markdown 10, Recharts, Three.js 0.183 with `@react-three/fiber` 9 and `@react-three/drei` 10.

**Scripts** ([frontend/package.json](frontend/package.json)):

```bash
npm run dev     # next dev, port 3000
npm run build   # next build
npm run start   # next start
npm run lint    # eslint
```

**Routes** (under [frontend/app/](frontend/app/)):

| Route                | Purpose |
|----------------------|---------|
| `/`                  | **Marketing landing page** — parallax sections (Hero with 3D vest, live telemetry showcase, 12 specialists grid, vest deep-dive, CTA footer) driven by Framer Motion + Lenis smooth scroll |
| `/login`             | JWT login form + dev-credential hint |
| `/register`          | New-patient self-registration form |
| `/dashboard/patient` | Patient-facing dashboard — biometric grid, waveforms, expert summaries, scenario picker |
| `/dashboard/doctor`  | Clinician-facing dashboard — patient roster shortcuts + multi-patient triage view |
| `/patients`          | Patient roster table with search + active-patient switcher |
| `/patients/[id]`     | Per-patient detail view — vitals, history, interpretations |
| `/cardiology`        | Dual-ECG leads I/II/III, PPG, HR, HRV, QRS, PR, cuffless BP, arrhythmia/ST-segment flags |
| `/obstetrics`        | FHR + CTG, contractions, kicks, maternal HR/temp, Dawes-Redman |
| `/respiratory`       | Pneumogram, lung-sound I²S stream, RR, SpO₂, tidal volume, COPD/apnea/hypoxia flags |
| `/neurology`         | Dual-IMU posture, gait symmetry, tremor, fall risk, autonomic HRV LF/HF |
| `/digital-twin`      | Full-screen 3D anatomical model + telemetry HUD + **PK/PD Simulator** panel (drug picker, dose slider, CYP2D6 toggle, live Bateman effect-curve chart) |
| `/diagnostics`       | Multi-agent cross-evaluation with per-agent confidence |
| `/environment`       | BMP280 + DHT11 ambient telemetry; DS18B20 × 3 skin-temp strip |
| `/alerts`            | Alert inbox + acknowledgement UI for triggered thresholds |
| `/handoff`           | Shift-handoff summary page — synthesised patient brief for the incoming clinician |
| `/admin/audit`       | Audit-log viewer (auth events, data access, scenario changes) |
| `/fhir-export`       | One-click FHIR R4 `Bundle` export — preview + download |
| `/settings`          | BLE device info, backend URL, stream rate, alert thresholds, system info |
| `/history`           | Resolution toggle (1m/1h) and 4-panel recharts grid (HR, SpO₂, RR, HRV) backed by `/api/history` |
| `/vest-viewer`       | Procedural 3D vest mesh inside `DashboardLayout` with a live sensor sidebar driven by `useVestStream`, scenario indicator, BLE status pill |

**Streaming hook** — [frontend/app/hooks/](frontend/app/hooks/) exposes `useVestStream()`, which opens an `EventSource` against `http://localhost:8000/stream`, parses the JSON payload, and auto-reconnects after 3 s on disconnect. State is managed with plain React hooks — no Redux / Zustand / Context provider.

**3D vest model** — [frontend/app/components/VestModel3D.tsx](frontend/app/components/VestModel3D.tsx). **Fully procedural — no .glb assets.** Built entirely from Three.js primitives + custom `BufferGeometry` (curved torso panels with neck cutout, side cummerbund extrudes, shoulder yoke ribbons), with realism details added through procedural `DataTexture` normal/roughness maps for woven fabric, dashed stitching tubes around every panel seam, a real centre zipper (tape + alternating teeth + slider + pull tab), flat webbing straps (tangent-aligned ribbon geometry, not tubes), and four sensor styles — medical ECG electrodes (silver hydrogel + snap stud), PPG sensors (black housing + 660 nm LED), DS18B20 temp pucks coloured by live skin temp, and perforated I²S mic grilles. Hover any sensor to surface a tooltip with its live channel + temperature. Two exports: `VestScene` (drop-in 3D content for any parent `<Canvas>`) and `VestModel3D` (self-contained with own Canvas + DOM overlays — used on `/vest-viewer`).

**Marketing landing page** — [frontend/app/page.tsx](frontend/app/page.tsx). Parallax scroll experience driven by [SmoothScroll.tsx](frontend/app/components/SmoothScroll.tsx) (Lenis singleton, custom ease-out, lerp 0.1) and Framer Motion's `useScroll` / `useTransform` / `whileInView`. Sections: sticky-blur top nav, hero with the procedural 3D vest in [HeroCanvas.tsx](frontend/app/components/HeroCanvas.tsx), live telemetry showcase with Framer-Motion-animated tickers, 12-specialist grid, vest deep-dive in [VestSectionCanvas.tsx](frontend/app/components/VestSectionCanvas.tsx), and a CTA footer.

**PK/PD Simulator** — [frontend/app/components/PharmacologyPanel.tsx](frontend/app/components/PharmacologyPanel.tsx). Mounted on `/digital-twin`. Drug picker (labetalol / oxytocin), dose slider 0–100 mg, CYP2D6 metabolizer toggle, and a 60-second `recharts` line of `pharmacology.effect_curve` (Bateman). Posts to `/api/simulation/medicate` and `/api/simulation/cyp2d6`; consumes the live SSE stream for the chart and the modulated vital-readout strip.

**Expert chat** — a right-side panel that lets you pick one of seven specialists and converse via text or Web Speech API voice I/O, with streaming markdown replies.

## Mobile app (mobile/aegis)

Flutter 1.0.0+1, Dart SDK `^3.11.0`. Targets Android, iOS, Web, Windows, macOS and Linux.

Dependencies ([mobile/aegis/pubspec.yaml](mobile/aegis/pubspec.yaml)): `provider`, `http`, `google_fonts`, `fl_chart`, `flutter_markdown`, `model_viewer_plus`, `webview_flutter`, `image_picker`.

Screens include Dashboard, Specialists (tabbed cardiology / neurology / obstetrics / respiratory / environment), Digital Twin (`model_viewer_plus`), Diagnostics, Settings. Services — `api_service.dart` and `vest_stream_service.dart` — mirror the web client's SSE/REST patterns.

## Firmware (PlatformIO/)

### Aegis vest — [PlatformIO/vest/](PlatformIO/vest/)

- **Board**: `esp32-s3-devkitc-1`, Arduino framework, 115200 baud.
- **Libs** ([platformio.ini](PlatformIO/vest/platformio.ini)): `h2zero/NimBLE-Arduino`, `sparkfun/SparkFun MAX3010x Pulse and Proximity Sensor Library`, `milesburton/DallasTemperature`.
- **BLE name**: `Aegis_SpO2_Live` — characteristic UUID `beb5483e-36e1-4688-b7f5-ea07361b26a8`.
- Emits the comma-separated key:value payload parsed by the backend.
- See [PlatformIO/vest/WIRING.md](PlatformIO/vest/WIRING.md) for the full pinout.

### Abdomen / fetal monitor — [PlatformIO/fetal_monitor/](PlatformIO/fetal_monitor/)

- **Board**: `esp32dev`, Arduino framework, partitioned `min_spiffs.csv`, pinned to `COM3` on Windows.
- **Libs** ([platformio.ini](PlatformIO/fetal_monitor/platformio.ini)): `adafruit/Adafruit ADS1X15`, `adafruit/Adafruit BusIO`, `bblanchon/ArduinoJson`.
- **BLE name**: `AbdomenMonitor` — characteristic UUID `12345678-1234-1234-1234-123456789ab1`.
- Emits a JSON payload with `mode`, piezo × 4, kicks × 4, movement × 4, mic × 2, heart tones × 2, bowel × 2, film pressure × 2, contractions × 2.

### Firmware sample-rate architecture

A common confusion: "just change `delay(25)` to `delayMicroseconds(4000)` in `main.cpp`" — **that instruction does not apply to this firmware**. The vest runs a cooperative tick loop driven by `millis()` comparisons, not a single-rate `delay()`. The intervals are declared in [config.h:50-58](PlatformIO/vest/src/config.h#L50):

```cpp
#define PPG_READ_INTERVAL    25    // 40 Hz  — MAX30102 polling
#define IMU_READ_INTERVAL    50    // 20 Hz  — MPU6050 pitch/roll
#define ECG_SAMPLE_INTERVAL  3     // 333 Hz — AD8232 ADC read into ring buffer
#define ECG_PROCESS_INTERVAL 1000  // 1 Hz   — publishes latest ECG sample to BLE payload
#define AUDIO_INTERVAL       1000  // 1 Hz   — I²S RMS
#define TEMP_READ_INTERVAL   5000  // 0.2 Hz — DS18B20 skin temps
#define ENV_READ_INTERVAL    5000  // 0.2 Hz — BMP280 + DHT11
```

**ECG is sampled at 333 Hz** into a 1024-sample ring buffer inside [ECGManager::sample()](PlatformIO/vest/src/ecg/ecg_manager.cpp).

**Earlier history (firmware ≤ v3.2):** [ECGManager::process()](PlatformIO/vest/src/ecg/ecg_manager.cpp) ran every `ECG_PROCESS_INTERVAL` (1000 ms) and copied **one** sample from the ring buffer into `ecgData.lead1_mv/lead2_mv/lead3_mv`; [BLEManager::transmit()](PlatformIO/vest/src/ble/ble_manager.cpp) baked those scalars into the vitals payload. Effective ECG rate delivered to the backend was **~1 Hz**, even though sampling itself was 333 Hz — the 332 other samples per second were overwritten in the ring buffer and never seen.

**Current path (firmware v3.3+):** raw ECG ships on a **dedicated BLE characteristic** (`beb5483e-…-26a9`) at the firmware sample rate. The vitals characteristic no longer carries `L1`/`L2`/`L3` — only the derived HR + status flags. The flow:

1. `ECGManager::sample()` writes ADC reads into the 1024-sample ring buffer at 333 Hz and increments `_pendingCount`.
2. `ECGManager::drainSamples(lead1, lead2, max)` copies up to 16 fresh samples (oldest-first), advances the drain pointer, and returns the count. Pending samples beyond the cap are kept for the next drain — no silent drops unless the ring overflows.
3. `BLEManager::transmitECGBurst(ecg)` runs every `ECG_BURST_INTERVAL` (33 ms ≈ 30 Hz), drains the manager, and emits a compact ASCII payload `EB1:v0|v1|...,EB2:v0|v1|...` (≤ 256 bytes) on the burst characteristic.
4. Backend [`handle_ecg_burst()`](app.py) parses the burst, appends each sample to `ecg_l1_data`/`ecg_l2_data`, and computes Lead III (`II - I`) per sample.

Net delivered ECG rate: **~333 Hz** (firmware-side cap; NimBLE notify throughput on ESP32 typically sustains 30+ Hz × 11 samples/burst). The backend deque is sized as `MEDVERSE_ECG_SAMPLE_RATE × 4 s` (default `250 × 4 = 1000` samples) — keep this independent of the vitals `MEDVERSE_SAMPLE_RATE` so PPG and ECG can scale separately.

**Backwards compatibility:** `handle_ble_notification` still parses optional `L1`/`L2`/`L3` from the vitals payload, so vests on pre-v3.3 firmware keep working at 1 Hz until reflashed. Backend's `run_single_client` skips the burst characteristic with a warning when the firmware doesn't expose it.

### Hardware matrix

| Device           | MCU         | Sensors                                                            | BLE name          |
|------------------|-------------|--------------------------------------------------------------------|-------------------|
| Aegis Vest       | ESP32-S3    | MAX30102 × 3, MPU6050 × 2 (in GY-87 + dedicated IMU), DS18B20 × 3, AD8232 3-lead, BMP180, BMP280, DHT11, I²S mic | `Aegis_SpO2_Live` |
| Abdomen Monitor  | ESP32 (dev) | Piezo × 4, MEMS mic, flex film, ADS1115 16-bit ADC                 | `AbdomenMonitor`  |

## ML pipelines (models/)

[models/](models/) is reorganised as **12 self-contained pipelines** — one per source experiment notebook. Each pipeline owns its data ingestion, validation, transformation, and trainer; the canonical structure is documented in [models/README.md](models/README.md) and discoverable programmatically via [models/registry.py](models/registry.py).

```
models/
├── README.md              # canonical structure + per-pipeline index
├── registry.py            # PIPELINES registry (slug, family, modality, paths)
├── _template/             # reference implementation for new pipelines
└── <slug>/
    ├── main.py            # entry point — runs ingestion → validation → transform → train
    ├── data_schema/schema.yaml   # expected columns + target (drives validation)
    ├── notebooks/source.ipynb    # original experiment notebook
    └── src/
        ├── components/{data_ingestion,data_validation,data_transformation,model_trainer}.py
        ├── entity/{config_entity,artifact_entity}.py
        ├── pipeline/training_pipeline.py
        ├── exception/exception.py    # MedVerseException wrapper
        ├── logging/logger.py
        └── utils/main_utils/utils.py
```

### Pipeline registry

| Pipeline            | Family       | Dataset          | Source                                | Auth required          | Auto-downloads |
|---------------------|--------------|------------------|---------------------------------------|------------------------|----------------|
| `ecg_biometric`     | metric-learn | ECG-ID (~100 MB) | PhysioNet `ecgiddb/1.0.0`             | none                   | ✅ on first run |
| `parkinson_screener`| classify     | UCI Parkinsons + WearGait-PD | UCI HTTP + Synapse `syn52540892` | `SYNAPSE_AUTH_TOKEN` (gait only) | Voice features ✅; gait skipped without token |
| `fetal_health`      | classify     | UCI CTG (+ CTU-UHB) | UCI XLS + PhysioNet `ctu-uhb-ctgdb` | none (CTU behind `MEDVERSE_FETCH_LARGE`) | UCI ✅; CTU gated |
| `preterm_labour`    | classify     | TPEHGDB + TPEHGT (~500 MB) | PhysioNet                       | none                   | ✅ on first run |
| `lung_sound`        | classify     | ICBHI 2017 (~600 MB) | direct ZIP mirror (Kaggle fallback) | none (Kaggle optional)| ✅ on first run |
| `bowel_motility`    | classify     | synthetic        | local generator from notebook         | none                   | ✅ always synthetic |
| `stress_ans`        | classify     | synthetic / WESAD | local generator (or `WESAD_ROOT`)    | email reg for real WESAD | ✅ synthetic by default |
| `ecg_arrhythmia`    | classify     | PTB-XL (~25 GB)  | PhysioNet `ptb-xl/1.0.3`              | none                   | gated by `MEDVERSE_FETCH_LARGE` |
| `cardiac_age`       | regress      | PTB-XL + PTB (~32 GB) | PhysioNet                        | none                   | gated by `MEDVERSE_FETCH_LARGE` |
| `skin_disease`      | classify     | HAM10000 (+ ISIC) | Kaggle `kmader/skin-cancer-mnist-ham10000` | `KAGGLE_USERNAME` + `KAGGLE_KEY` | HAM10000 with creds; ISIC gated by `MEDVERSE_FETCH_LARGE` |
| `retinal_disease`   | classify     | ODIR-5K (~3.5 GB) | Kaggle `jeftaadriel/oia-odir-dataset` | `KAGGLE_USERNAME` + `KAGGLE_KEY` | ✅ with creds |
| `retinal_age`       | regress      | ODIR-5K + RETFound MAE weights | Kaggle + HuggingFace `rmaphoh/RETFound_MAE` | `KAGGLE_*` + `HF_TOKEN` | ✅ with creds |

When a pipeline can't proceed (large gate off, missing credentials, missing module), `pipeline_utils.DatasetUnavailable` is raised with a clear `.hint` describing exactly what to set.

### Running pipelines

```bash
# One pipeline at a time
cd models/ecg_biometric && python main.py

# All 12 pipelines in sequence with per-pipeline timeouts + status JSON
python train_all.py

# Subset of pipelines
python train_all.py --only ecg_biometric,parkinson_screener,fetal_health

# Skip the slow ones
python train_all.py --skip ecg_arrhythmia,cardiac_age,retinal_age

# Opt into the large datasets for this run (otherwise gated pipelines raise DatasetUnavailable)
python train_all.py --large

# Custom timeout (seconds) and results path
python train_all.py --timeout 600 --results train_all_results.json
```

`train_all.py` writes `train_all_results.json` after each pipeline so partial runs are durable. Each entry classifies the outcome as `ok` / `gated` / `timeout` / `fail`.

### Shared dataset helpers

[pipeline_utils.py](pipeline_utils.py) provides the cross-pipeline plumbing called from every `_load_dataframe` override:

- `cache_dir(slug, sub)` — anchored at the project root, returns `models/<slug>/data/<sub>/`.
- `is_large_allowed()` — reads `MEDVERSE_FETCH_LARGE`.
- `require_env(*names, hint=…)` — raises `DatasetUnavailable` listing missing variables and what to set.
- `require_module(name, install_hint=…)` — lazy-import; raises with the exact `pip install` line when missing.
- `download_file(url, target, sha256=…)` — HTTP download with `tqdm` progress + SHA256 verify + skip-if-exists.
- `download_physionet(records_url, target_dir)` — recursive PhysioNet wget with cache short-circuit.
- `download_kaggle_dataset(slug, target)` — Kaggle Python API (not subprocess); auto-unzips.
- `download_huggingface_file(repo_id, filename, target)` — `hf_hub_download` wrapper for single-file artefacts (e.g. RETFound weights).
- `download_synapse_entity(entity_id, target)` — Synapse client wrapper for WearGait-PD.

Per-pipeline `data_ingestion.py` files use marker-file checks (e.g. `ptbxl_database.csv` for PTB-XL, ≥70 `Person_*` dirs for ECG-ID, ≥250 `.hea` files for TPEHGDB) so partial caches are never treated as complete.

### Runtime adapters (legacy)

Pre-existing adapters in [src/ml/](src/ml/) and [src/biometric/](src/biometric/) (`ECGFounderAdapter`, `RespiratorySoundClassifier`, `ECGBiometric`) report `is_loaded = False` until weights land under `MEDVERSE_MODELS_DIR`; the graphs fall back to LLM-only assessment. The 12 pipelines above produce sklearn baselines today; swapping each one for the production architecture from its source notebook is a per-pipeline `_build_model` override.

## Development notes

- **Mock mode** is automatic — if `bleak` cannot find either BLE device within 10 s, `start_mock_data()` takes over at 40 Hz.
- **CORS** is driven by `MEDVERSE_CORS_ORIGINS` (default `localhost:3000,127.0.0.1:3000`). Add entries there before deploying behind a different origin.
- **Auth** is off by default (`MEDVERSE_AUTH_ENABLED=false`); every FHIR endpoint already has `Depends(require_user)` attached so flipping the flag is all it takes to protect them.
- **Embedding dimensionality** differs between BioLORD (768) and MiniLM (384). The Chroma collection name includes a suffix derived from the active model, so switching models creates a fresh collection instead of corrupting the existing one — see [src/utils/vector_store.py](src/utils/vector_store.py).
- **Waveform in SSE** — `MEDVERSE_INCLUDE_WAVEFORM=true` inflates each snapshot by roughly 40× (800 samples × 6 channels). Only turn it on when the ML adapters are loaded and need the raw window.
- **Buffer sizing** — all channels keep the last 800 samples (~20 s at 40 Hz). SpO₂ uses the last 160 (`SPO2_WINDOW`); BR uses the last 400 (`BR_WINDOW`).
- **Chroma** gracefully degrades — if embeddings cannot be loaded, interpretations still flow but without prior-session context.
- **LangGraph CLI** — `langgraph dev` will pick up [langgraph.json](langgraph.json) and boot an in-memory checkpoint store; state is persisted to `.langgraph_api/`.
- **Frontend-backend port contract** is hard-coded (`:8000` in the frontend, `:3000` for the dashboard). Change both sides together if you move them.

## Troubleshooting

| Symptom                                                 | Likely cause / fix |
|---------------------------------------------------------|--------------------|
| Backend logs `[WARN] Device '…' not found.`             | Expected if hardware is off — you'll get mock data. |
| Frontend stuck at "connecting" / empty graphs           | Backend isn't running, or your dev origin isn't in `MEDVERSE_CORS_ORIGINS` — confirm `curl http://localhost:8000/api/status`. |
| `401 Unauthorized` from every `/api/**` call            | `MEDVERSE_AUTH_ENABLED=true` is set. Either flip it to `false` or fetch a token via `POST /api/auth/login`. |
| Groq 429 / rate-limit errors                            | Give each specialty its own key in `.env` (see [Environment variables](#environment-variables)). |
| `fetal_connected` stays `false`                         | AbdomenMonitor not advertising, or COM3 is wrong for your setup — edit [PlatformIO/fetal_monitor/platformio.ini](PlatformIO/fetal_monitor/platformio.ini). |
| `PATIENT_CYP2D6_STATUS` never updates                   | `/api/upload-lab-results` falls back to `Poor Metabolizer` when the upload is not a PNG/JPG or the vision call fails. |
| `bleak` import fails                                    | `pip install bleak` — mock mode also kicks in automatically. |
| `/api/history` returns an empty list                    | Stream data for a minute or two so SQLite accumulates rows. On Timescale, check that `CREATE EXTENSION timescaledb` ran and `alembic upgrade head` completed. |
| History chart flatlines at 1 m resolution               | Not enough rows in the last minute — switch to `1h`. |
| Sample rate mismatch (backend says 40, firmware on 250) | Read [Firmware sample-rate architecture](#firmware-sample-rate-architecture) first — the edit is in [config.h](PlatformIO/vest/src/config.h), not a `delay(25)` in `main.cpp`. After flashing the new firmware, set `MEDVERSE_SAMPLE_RATE=250` in `.env`. The active rate appears in `GET /api/status` so the frontend can verify sync. |
| ECG window filled with repeating values                 | Vest is on pre-v3.3 firmware (still emitting `L1`/`L2`/`L3` scalars in the vitals payload, no burst characteristic). Reflash with the current firmware — the burst path delivers true 333 Hz on `beb5483e-…-26a9`. Backend warns `Optional char ... unavailable` when the burst char isn't exposed. |
| Flutter `invalid credentials` on login                  | Backend auth is off by default — any creds should succeed. If it still fails, confirm `ApiConfig.baseUrl` resolves (Android emulator auto-maps `localhost` → `10.0.2.2`). |
| Mobile login screen stays visible after valid login     | `AuthService.load()` may have thrown — check debug console. `flutter_secure_storage` needs MainActivity to use `FlutterFragmentActivity` on Android API < 23. |
| FHIR endpoints return dicts, not validated resources    | `pip install fhir.resources>=7.0.0` — the module falls back to raw dicts when it's absent. |
| ML adapters log "weights not found"                     | Expected until you train + drop files under `MEDVERSE_MODELS_DIR`. Graphs fall back to LLM-only. |
| Chroma errors about dimension mismatch after model swap | Expected once — the new embedder creates a fresh collection. Old vectors persist under their old suffix until you delete `chroma_data/<key>_<old-model>/`. |
| BioLORD first load is slow                              | The first call downloads ~1.5 GB of weights to the HF cache. Set `MEDVERSE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2` to stay on the lighter model. |
| `alembic upgrade head` fails with "extension not found" | Run `CREATE EXTENSION IF NOT EXISTS timescaledb;` in your Postgres before applying. |

## Security notice

MedVerse ships **security-capable but not security-mandatory** — auth is off by default so newcomers can run it in one step, and every security surface is a single env flip away from production posture:

- **Auth**: set `MEDVERSE_AUTH_ENABLED=true` and provide a strong `MEDVERSE_JWT_SECRET` — startup hard-fails if auth is on and the secret is unset or matches the obvious dev placeholders. With auth off, the backend generates an ephemeral per-process secret (tokens won't survive a restart). Every `/api/**` route already has `Depends(require_user)` attached, and `/stream` enforces `?token=` when auth is on.
- **CORS**: allowlist is driven by `MEDVERSE_CORS_ORIGINS` (default: `localhost:3000` only). Never set it to `*` on a deployed backend.
- **Groq keys**: the committed [.env](.env) holds real-looking keys from earlier iterations. **Before sharing this repo** — rotate every `gsk_…` key at https://console.groq.com, ensure [.env](.env) stays in [.gitignore](.gitignore), and scrub Git history with `git filter-repo` or BFG.
- **Frontend JWT storage**: `localStorage.medverse_token`. Swap for HttpOnly cookies before any production deployment that touches real patient data.
- **Mobile JWT storage**: `flutter_secure_storage` (Keychain on iOS, EncryptedSharedPreferences on Android) — already wired.

## Roadmap

### Done

- ✅ Two-compartment Bateman PK/PD with CYP2D6-aware clearance.
- ✅ IMU-derived biomarkers (tremor, gait, POTS, activity state).
- ✅ FHIR R4 `Observation` / `Bundle` / `DiagnosticReport` / `Patient` / `Device` endpoints.
- ✅ JWT bearer auth + env-driven CORS allowlist (feature-flagged off by default).
- ✅ Env-driven sample rate + derived buffer sizes (firmware-ready for 250 Hz).
- ✅ Dawes-Redman CTG surrogate with 30-minute ring buffer.
- ✅ `patient_id` propagation — SSE query param, JWT `sub`, DB rows, `/api/patient/active` endpoint.
- ✅ SQLite / TimescaleDB conditional writer — flip by setting `MEDVERSE_DB_URL`.
- ✅ `/api/history` endpoint (SQLite Python-bucketed or Timescale continuous aggregate).
- ✅ Frontend `NEXT_PUBLIC_API_URL` + shared `lib/api.ts` client + bearer-token SSE.
- ✅ `/login` page + recharts-powered `/history` dashboard.
- ✅ Flutter `AuthService` + login gate + `flutter_secure_storage` + centralised `ApiConfig`.
- ✅ Biomedical RAG — default embedding swapped to `FremyCompany/BioLORD-2023`.
- ✅ Runtime adapters scaffolded — ECGFounder, respiratory CNN, ECG biometric (weights pluggable).
- ✅ Federated-learning client wired to real SQLite ECG windows + 3-layer 1-D CNN.
- ✅ TimescaleDB migration under `alembic/` (hypertables + 1m/1h continuous aggregates).
- ✅ Safe `.env.example` + `frontend/.env.example`; `.env`, local DBs, ML weights gitignored.
- ✅ **12 self-contained ML pipelines** under `models/<slug>/` — one per source experiment notebook, each with its own `main.py` + `data_schema/schema.yaml` + 4-stage component graph.
- ✅ **Cross-pipeline runner** [train_all.py](train_all.py) — invokes every pipeline with per-pipeline timeouts, classifies outcomes (ok / gated / timeout / fail), persists `train_all_results.json` incrementally, supports `--only` / `--skip` / `--large` filters.
- ✅ **Shared dataset loader** [pipeline_utils.py](pipeline_utils.py) — PhysioNet wget, Kaggle Python API, HuggingFace Hub, Synapse client, marker-file cache validation, `DatasetUnavailable` exception with actionable hints.
- ✅ Smart download policy — small/auth-free datasets auto-download; large datasets gated behind `MEDVERSE_FETCH_LARGE`; auth-required pipelines gated behind credentials.
- ✅ **Parallax marketing landing page** at `/` — Lenis smooth-scroll, Framer Motion `useScroll` parallax, sticky-blur top nav, 12-specialist grid, vest deep-dive, animated telemetry tickers.
- ✅ **Procedural 3D vest** — fully built from Three.js primitives + procedural fabric/webbing `DataTexture` normal maps (no .glb assets); realistic stitching, centre zipper, flat webbing straps, 4 sensor styles (ECG electrode / PPG / DS18B20 / I²S mic), control module with vents + USB-C cutout.
- ✅ Patient identity, alerts, care plans, audit log, FHIR export, handoff, doctor/patient dashboard split, register flow.
- ✅ **ECG burst characteristic (firmware v3.3)** — dedicated BLE char `beb5483e-…-26a9` carries raw 333 Hz ECG via `EB1:`/`EB2:` compact ASCII batches; backend `handle_ecg_burst` appends per-sample and computes Lead III. Replaces the 1 Hz scalar path. Backwards-compatible — old firmware still works at 1 Hz via `L1`/`L2`/`L3` in vitals payload.
- ✅ **Vest firmware bug-stop pass (v3.4)** — five real bugs caught in audit and fixed:
  - MAX30102 die-temperature was refreshing every ~125 s instead of every 5 s (`_tempCounter` compared a millis-defined constant against a loop count). Replaced with a `millis()` timer.
  - ECG R-peak detection used a hard-coded 1980 mV threshold (60% of supply) that real AD8232 signals never reach. Replaced with adaptive baseline + envelope tracker (50% of recent peak amplitude, 100 mV floor) running per-sample at 333 Hz inside `sample()` instead of at the slower `process()` cadence.
  - DHT11 bit-banged read was preempted by FreeRTOS task switches mid-frame, corrupting bit timing. Wrapped the 40-bit loop in `taskENTER_CRITICAL` and throttled the checksum-fail log so noisy lines don't flood Serial.
  - Audio "sound detected" used a hard-coded RMS threshold with no calibration, so the flag either fired constantly or never depending on mic DC bias. Ported the fetal_monitor's rolling-baseline pattern (16-sample window, only updates during quiet periods).
  - `BLEManager::transmit()` was called every loop iteration (200+ Hz with mostly stale data, stealing notify slots from the ECG burst). Throttled to a dedicated 25 Hz `BLE_TX_INTERVAL` clock.
- ✅ **Reliability + performance pass (firmware v3.4)** — eight more wins, all software-side:
  - **Vest IMU** targeted-ping at MPU6050 0x68 replaces the 1-127 sweep that previously took several seconds at boot. *(v3.4 also moved the IMU to hardware `TwoWire(2)` — that turned out to be wrong: ESP32-S3 has only 2 I²C peripherals, both already claimed by the MAX30102 sensors, so `TwoWire(2)` silently mapped to bus 0 and broke the IMU. Reverted in v3.5 back to bit-banged software I²C; targeted ping kept.)*
  - **Vest sensor scan** trimmed from 1-127 with 50 ms-per-address timeout (~6.3 s worst case per bus, two buses) to a single targeted MAX30102 ping at 0x57. `_resetBus` settle drop 200 ms → 20 ms; back-to-back `bus.begin` settles consolidated to a single 20 ms.
  - **Vest setup** `delay(5000)` "wait for serial" → `delay(100)`. Saves ~5 s of boot tax.
  - **Vest DHT11** first-read deferred out of `begin()`. Used to add a synchronous 1 s `delay()` plus a probe that frequently failed at boot before pinModes settled.
  - **Watchdog** timer enabled on both firmwares (10 s). Hung blocking calls now reboot cleanly instead of locking the device. Fed once per loop iteration + during ADS retry waits.
  - **Fetal piezo** ADC reads switched to `analogReadMilliVolts()` so the per-chip eFuse calibration corrects for the ESP32-Classic ADC's nonlinear S-curve. ADC attenuation set to `ADC_11db` to match 3.3 V piezo range. Baseline now force-drifts after 30 s of sustained event so a long contraction can't freeze the threshold.
  - **Fetal ADS1115** sample rate bumped 128 SPS → 860 SPS (read latency 10 ms → 5 ms per channel; full 4-ch pass 40 ms → 20 ms). I²C bus bumped 100 kHz → 400 kHz. ADS init no longer hard-halts on missing chip — retries every 2 s with WDT pets.
  - **Vest firmware version** now embedded in the BLE vitals payload as `FW:3.4`. Backend logs the value once per session so a vest still on old firmware is immediately visible in the console.
  - Root `.gitignore` extended to cover `PlatformIO/**/.pio/` and `PlatformIO/**/.venv/`. Dead code in `PlatformIO/vest/backup/` (ecg.cpp + led.cpp) removed.
- ✅ **Fetal-monitor BLE migration to NimBLE + ASCII payload** — replaced the bundled Bluedroid BLE stack with `h2zero/NimBLE-Arduino @ ^1.4.3` (frees ~70 KB of RAM, parity with the vest firmware, NimBLE auto-creates the CCCD descriptor so the manual `BLE2902` attach is gone). Sensor payload switched from per-publish heap-alloc `JsonDocument` to a stack-allocated 256 B `key:value,...` ASCII format mirroring the vest's vitals layout. Backend `handle_fetal_notification` now auto-detects on the leading character (`{` → legacy JSON, anything else → compact ASCII) so vests on old firmware keep working until reflashed. `ArduinoJson` dropped from `lib_deps`.
- ✅ **Heart-tone classifier rewrite** — replaced the hard-coded `0.001 < energy < 0.05 → heart` magic numbers (which assumed a fixed MAX9814 gain that the chip's AGC actively defeats) with a self-calibrating, rhythm-based detector. Tracks recent peak timestamps in a per-channel ring buffer; classifies as fetal heart tone when ≥3 inter-peak intervals land in the 333–545 ms window (110–180 bpm). Bowel sound = sustained energy elevation that is NOT rhythmic. Still a heuristic — true fetal-HR extraction needs proper band-pass + autocorrelation in the envelope band — but this one actually adapts to the installed mic gain.
- ✅ **NimBLE-Arduino patch bump** — vest goes 1.4.1 → ^1.4.3 (bug fixes within the 1.x line, no API breaks). Stays off 2.x because the `onConnect/onDisconnect` callback signature change is API-breaking and we can't run an integration test cycle in CI.
- ✅ **Log-level macros** added to both `config.h` files — `LOG_ERR`/`LOG_WARN`/`LOG_INFO`/`LOG_DEBUG` gated by a `LOG_LEVEL` define (default 2 = INFO+). New code can use these; existing `Serial.printf` calls are left in place to avoid pure-churn diffs. Production builds can compile out chatty logs with `-DLOG_LEVEL=0`.
- ✅ **Vest v3.5 hot-fix pass** — caught from on-device serial output:
  - **IMU regression** from v3.4 reverted (see above note). IMU now reads pitch/roll/BMP180 again.
  - **DS18B20 -127 sentinel filter** — DallasTemperature library returns -127 °C when a probe momentarily fails to ACK. We now hold the previous reading for any value outside the physiological 25-45 °C window, so a momentary glitch no longer renders as a huge red spike on the dashboard or in the ML pipelines.
  - `FW_VERSION` bumped 3.4 → 3.5 so the backend's `[VEST] Firmware version: 3.5` log confirms the reflash actually landed.
- ✅ **Vest v3.6 + v3.7 field-fix pass** — caught from on-device serial output after v3.5 reflash:
  - **ECG dual-lead R-peak detection** — was locked to Lead II, but real electrode placement on this vest puts the dominant QRS on Lead I (~880 mV peak-to-peak vs Lead II's ~340 mV). Now tracks baseline + envelope on both leads and detects on whichever currently has the larger envelope — self-selects per wearer.
  - **ECG refractory period** — physiological max HR is ~220 bpm = 273 ms between R peaks. The previous detector unconditionally updated `_lastBeat` on every rising edge, so noise bumps reset the timer and the next real beat measured a sub-300 ms interval that failed validity. Now `_lastBeat` only advances when the new beat is past the refractory window.
  - **BMP180 counterfeit-cal protection** — many cheap GY-87 modules ship with a clone BMP180 whose temperature-related calibration registers (AC5/AC6/MC/MD) are correct but whose pressure-related registers (AC1/AC2/AC3/AC4/B1/B2) are out of datasheet range. Symptom: temp reads correctly (~33 °C), pressure outputs nonsense (~1613 hPa). v3.6 logs all calibration values during boot so the chip can be identified, and clamps published pressure to 800-1100 hPa with last-good fallback. The HW-611 BMP280 right next door reads correctly, so we don't actually lose pressure data.
  - **INMP441 sample shift** — `>> 11` was over-aggressive (divides 24-bit samples by 2048), flooring typical room-noise levels to zero before RMS, hence `Audio D:0` forever. Replaced with the standard `>> 8` which sign-extends the 24-bit MSB-justified sample into the int32 word.
  - `FW_VERSION` bumped 3.5 → 3.6 → 3.7 so each reflash is unambiguously visible in the backend log.
- ✅ **Phase 1 of agentic upgrade — collaborative diagnosis graph** — new top-level `complex_diagnosis_graph` (registered in [langgraph.json](langgraph.json)) implements the agentic-AI paper's Disease Proposer + Rare/Related Agent + Skeptic + Diagnosis topology with an Agentic-Brain–style planner. 7 nodes:
  - `planner_node` — rule-based gating (deterministic) — selects which downstream specialty graphs warrant invocation given current vitals + IMU + fetal state, instead of always running all 6
  - `disease_proposer_node` (LLM) — initial 3-7 common-to-uncommon differential
  - `rare_disease_agent_node` — Chroma similarity lookup against the bundled [data/rare_diseases.jsonl](data/rare_diseases.jsonl) snapshot (32 conditions across all 7 specialties; live Orphanet API deferred to Phase 5 once consent model exists)
  - `related_disease_finder_node` — KB-similarity expansion of confusables for each existing candidate
  - `background_agents_node` (LLM) — attaches per-candidate evidence (supports/contradicts/neutral with weights) using the actual telemetry features
  - `skeptic_node` (LLM) — actively disconfirms each candidate; pulls weak scores down so real diagnoses surface by elimination
  - `diagnosis_agent_node` (LLM) — final ranking + recommended next tests + clinician-facing narrative
  
  Every node emits structured `ReasoningStep` dicts into the shared `traces` accumulator, so the entire chain of reasoning is auditable. New endpoint `POST /api/agent/complex-diagnosis?patient_id=...` returns ranked candidates + evidence + planner gating + recommended tests + summary + full trace, and persists the synthesis as a `Collaborative Diagnosis` interpretation row visible on the existing diagnostics dashboard. Frontend [`CollaborativeDiagnosis.tsx`](frontend/app/components/CollaborativeDiagnosis.tsx) (mounted on `/diagnostics`) provides a one-click run button, ranked candidate cards with score bars + evidence pills + per-candidate test lists, and a collapsible reasoning trace tree. LLM-using nodes degrade gracefully when `GROQ_API_KEY` is absent — the graph still produces a (less rich) deterministic output.
- ✅ **Phase 2.A of agentic upgrade — obstetrics + retina runtime adapters** — 4 new ML adapters wired into the LangGraph specialty graphs so the LLM specialists reason on structured ML evidence, not just raw vitals. New shared base [`PickledTabularAdapter`](src/ml/_pickle_adapter.py) handles weight-load gating + sklearn pickle inference, used by:
  - [`fetal_health_adapter.py`](src/ml/fetal_health_adapter.py) — UCI CTG 3-class (Normal/Suspect/Pathological), feature map pulls from the live Dawes-Redman analyser block
  - [`preterm_labour_adapter.py`](src/ml/preterm_labour_adapter.py) — TPEHGDB EMG-derived binary risk (Term/PretermRisk)
  - [`retinal_disease_adapter.py`](src/ml/retinal_disease_adapter.py) — ODIR-5K 8-class fundus disease classifier; `predict_with_image()` accepts uploaded fundus image paths
  - [`retinal_age_adapter.py`](src/ml/retinal_age_adapter.py) — biological retinal age regression with delta-vs-chronological computation (positive delta → accelerated aging flag)
  
  Each pipeline gains an `export_runtime.py` (e.g. [`models/fetal_health/export_runtime.py`](models/fetal_health/export_runtime.py)) that loads the latest trained `ModelEstimator` from `artifacts/<ts>/`, extracts the sklearn-native preprocessor + model into a plain dict, and writes it to `${MEDVERSE_MODELS_DIR}/<domain>/<slug>/model.pkl` where the runtime adapter looks for it. This avoids the cross-pipeline `src.` namespace collision that prevents direct unpickling. [`graph_factory._augment_with_ml_models()`](src/graphs/graph_factory.py) now has obstetrics + ocular branches that gate on `adapter.is_loaded` and attach `fetal_health_prediction`, `preterm_labour_prediction`, `retinal_disease_prediction`, `retinal_age_prediction` to `tool_results` as JSON. New utility [`src/utils/image_loader.py`](src/utils/image_loader.py) (lazy-PIL, ImageNet-style normalisation) is in place for the upcoming image-aware model upgrade.
  
  New endpoint `POST /api/upload-image?modality=retinal|skin&patient_id=...` persists uploads to `uploads/<patient>/<modality>/<ts>.png` and surfaces the latest image of each modality on the snapshot under `imaging.{retinal,skin}.image_path` (gated by `MEDVERSE_INCLUDE_IMAGING=true` for the SSE stream; the complex-diagnosis route always splices it in). New frontend [`ImageUploadWidget.tsx`](frontend/app/components/ImageUploadWidget.tsx) mounted on `/dashboard/patient` provides PNG/JPG upload (10 MB cap) for both modalities. All adapters return `None` on missing weights — the graph runs unchanged on a fresh install with no trained weights anywhere.
- ✅ **Phase 2.B of agentic upgrade — remaining 7 runtime ML adapters (cardiology / pulmonary / neurology / dermatology / GI)** — completes the pipeline-to-runtime bridge for every model under `models/<slug>/`:
  - [`ecg_arrhythmia_adapter.py`](src/ml/ecg_arrhythmia_adapter.py) — PTB-XL 5-class super-classes (NORM/MI/STTC/CD/HYP); runs alongside ECGFounderAdapter so the cardiology LLM gets two independent classifiers
  - [`cardiac_age_adapter.py`](src/ml/cardiac_age_adapter.py) — biological cardiac age regression with delta-vs-chronological computation (positive delta → accelerated cardiac aging flag), mirrors `retinal_age` shape
  - [`stress_ans_adapter.py`](src/ml/stress_ans_adapter.py) — WESAD-style 3-class autonomic state (baseline/stress/amusement); consumed by both Neurology and General Physician graphs
  - [`lung_sound_adapter.py`](src/ml/lung_sound_adapter.py) — ICBHI patient-level diagnostic (Healthy/COPD/Asthma/etc); derives RMS + ZCR + percentile features from the audio waveform when available
  - [`parkinson_screener_adapter.py`](src/ml/parkinson_screener_adapter.py) — UCI Parkinsons voice-feature 22-dim classifier; cleanly skips when no voice features are supplied (vest doesn't capture voice — runtime usage is from a separate voice upload)
  - [`bowel_motility_adapter.py`](src/ml/bowel_motility_adapter.py) — 4-channel acoustic 3-class (quiet/normal/hyperactive); pulls from AbdomenMonitor piezo channels when present, falls back to vest mic
  - [`skin_disease_adapter.py`](src/ml/skin_disease_adapter.py) — HAM10000 7-class dermatoscopic classifier (akiec/bcc/bkl/df/mel/nv/vasc); same `predict_with_image` contract as the retina adapters
  
  Each pipeline gains an `export_runtime.py` (e.g. [`models/ecg_arrhythmia/export_runtime.py`](models/ecg_arrhythmia/export_runtime.py) — same template as Phase 2.A). [`graph_factory._augment_with_ml_models()`](src/graphs/graph_factory.py) extended with the new specialty branches: cardiology now has 3 adapter calls (ECGFounder + ecg_arrhythmia + cardiac_age), pulmonary 2 (RespCNN + lung_sound), neurology 2 (stress_ans + parkinson_screener), dermatology 1 (skin_disease via uploaded skin image), GP 2 (stress_ans + bowel_motility). All branches gate on `adapter.is_loaded` and a try/except so a single bad weight file can't break a graph run. With no weights anywhere, all branches emit empty `extras` and the graphs run identically to before — the upgrade is fully additive.
- ✅ **Phase 1.6 of agentic upgrade — selective specialty fan-out via planner** — patient_graph used to invoke ALL 6 specialty experts in parallel for every snapshot, regardless of vitals. Now there's a `planning_node` between `orchestrator` and the experts that runs the same rule-based gating used by `complex_diagnosis_graph` (one source of truth — `planner_node` in `src/nodes/complex_diagnosis_node.py`). The planner inspects HR / SpO₂ / RR / HRV + IMU biomarkers + fetal-monitor activity and writes `selected_specialties` to state; a LangGraph `add_conditional_edges` from `planning_node` then routes only to the matching expert nodes. Default for empty / missing-data snapshots: `[Cardiology + General Physician]` so the graph never deadlocks on an empty fan-out. General-physician fan-in works unchanged because LangGraph waits only on actually-invoked predecessors. Result: ~2–5× fewer Groq LLM calls per run on typical baseline snapshots, plus a tighter reasoning trace. `PatientWorkflowState` gains `selected_specialties`, `planner_rationale`, and a `traces: Annotated[list, operator.add]` accumulator; `_invoke_specialty_graph()` propagates each subgraph's `traces` upward so the unified UI sees one continuous chain of reasoning across the whole patient run. Also fixed a planner edge case where missing-vital sentinel zeros (firmware default) tripped bradycardia/bradypnea rules — the planner now uses `None`-aware comparisons so missing fields never trigger a specialty.

### User's to-do (not something I can do)

- **Reflash the vest** with current firmware to get the 333 Hz ECG burst path (`pio run -t upload` from [PlatformIO/vest/](PlatformIO/vest/)). Until reflashed, the vest stays on the 1 Hz scalar path and the backend logs `Optional char ... unavailable`.
- **Model training**: populate `models/ecg/ecgfounder/weights.pt`, `models/pulmonary/icbhi_cnn/weights.pt`, `models/ecg/biometric_siamese/weights.pt`.
- **Secrets**: rotate the committed `gsk_…` Groq keys and scrub Git history.
- **Clinical depth**: have a cardiologist / OB-GYN review [src/knowledge/*.md](src/knowledge/).
- **POTS calibration**: empirical threshold validation against a real sit-to-stand trial.
- **Deps**: `pip install -r requirements.txt`, `cd frontend && npm install`, `cd mobile/aegis && flutter pub get` — picks up `psycopg2-binary`, `recharts`, `flutter_secure_storage`.

## License

[MIT](LICENSE) © 2026 MedVerse Contributors.

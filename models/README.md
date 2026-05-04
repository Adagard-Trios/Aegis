# MedVerse — Model Pipelines

Twelve self-contained ML pipelines, one per clinical model. Every pipeline mirrors the same folder + code structure so they can be developed, tested, and deployed independently.

## Pipelines

| Folder | Notebook | Domain |
|---|---|---|
| [ecg_arrhythmia/](ecg_arrhythmia/) | ECG Arrhythmia Analyser | Cardiology |
| [cardiac_age/](cardiac_age/) | Cardiac Biological Age | Cardiology |
| [stress_ans/](stress_ans/) | Stress / ANS Classifier | Autonomic |
| [lung_sound/](lung_sound/) | Lung Sound Analyser | Pulmonary |
| [parkinson_screener/](parkinson_screener/) | Parkinson Screener | Neurology |
| [fetal_health/](fetal_health/) | Foetal Health Analyser | Obstetrics |
| [preterm_labour/](preterm_labour/) | Preterm Labour Predictor | Obstetrics |
| [bowel_motility/](bowel_motility/) | Bowel / GI Motility | GI |
| [skin_disease/](skin_disease/) | Skin Disease Detector | Dermatology |
| [retinal_disease/](retinal_disease/) | Retinal Disease Classifier | Ocular |
| [retinal_age/](retinal_age/) | Retinal Biological Age | Ocular |
| [ecg_biometric/](ecg_biometric/) | ECG Biometric Identity | Biometric ID |

The source experiment notebook for each pipeline lives at `<pipeline>/notebooks/source.ipynb`.

## Canonical structure

Every pipeline folder is identical:

```
<pipeline>/
├── README.md
├── app.py                            # FastAPI: GET /health, POST /predict
├── data_schema/schema.yaml           # input/output contract
├── notebooks/source.ipynb            # source experiment
└── src/
    ├── components/                   # data_ingestion, data_validation,
    │                                   data_transformation, model_trainer
    ├── constants/training_pipeline/  # paths + hyperparameters
    ├── entity/                       # *Config and *Artifact dataclasses
    ├── exception/                    # MedVerseException
    ├── logging/                      # rotating file logger
    ├── pipeline/                     # TrainingPipeline + BatchPrediction
    └── utils/
        ├── main_utils/utils.py       # save/load, yaml helpers
        └── ml_utils/
            ├── metric/__init__.py    # classification + regression metrics
            └── model/estimator.py    # ModelEstimator (preprocessor + model)
```

### Data flow

```
DataIngestion ─→ DataValidation ─→ DataTransformation ─→ ModelTrainer
   (split)          (schema +         (preprocess +        (fit +
                     drift report)     persist)             metrics)
```

Each component consumes the previous component's `*Artifact` dataclass and returns its own. `TrainingPipeline.start()` orchestrates the four stages and returns the final `ModelTrainerArtifact`.

## Quick start

### Train a single pipeline

```bash
cd models/<pipeline>
python main.py                                                    # train end-to-end
python -m src.pipeline.training_pipeline                          # equivalent
python -m src.pipeline.batch_prediction --input x.csv --output y.csv
uvicorn app:app --port 8001                                       # serve as microservice
```

### Train every pipeline at once

From the repo root:

```bash
python train_all.py                       # all 12 pipelines, .env auto-loaded
python train_all.py --large               # also runs the LARGE-gated ones (PTB-XL etc.)
python train_all.py --only fetal_health,parkinson_screener
python train_all.py --skip ecg_arrhythmia,cardiac_age
```

`train_all.py` reads the root `.env` (Kaggle / HF / Synapse creds + `MEDVERSE_FETCH_LARGE`)
and propagates it to every subprocess, prints a per-pipeline status table at the end,
and writes `train_all_results.json` with full details (test metrics + saved-model paths).

`main.py` is the canonical training trigger — every pipeline has an identical
copy that walks DataIngestion → DataValidation → DataTransformation →
ModelTrainer with explicit per-step logging. Use `python main.py` while
filling in stubs (clearer error frames); use the `-m src.pipeline...` form
in CI / production orchestrators.

The skeleton's logger, exception wrapper, config/artifact dataclasses, and orchestrator are functional out-of-the-box. The two methods that **must** be filled in for any real run:

- `DataIngestion._load_dataframe()` — return the raw `pd.DataFrame` for this model
- `ModelTrainer._build_model()` — return an unfitted estimator (sklearn / torch / lightgbm)

Each raises `NotImplementedError` until you fill it in, so an unconfigured pipeline fails fast with a clear message.

## Adding a new pipeline

1. `cp -r <existing_pipeline> <new_pipeline>` — the structure is the contract.
2. Replace `notebooks/source.ipynb` with the new notebook.
3. Update `README.md` title and `src/constants/training_pipeline/__init__.py:PIPELINE_NAME`.
4. Override `DataIngestion._load_dataframe` and `ModelTrainer._build_model`.
5. Update `data_schema/schema.yaml` with the input/target columns.
6. Add the entry to [registry.py](registry.py).

## Programmatic discovery

[registry.py](registry.py) lists every pipeline so the main FastAPI backend
(`src/ml/`) and ops scripts can iterate without hardcoding paths.

## Datasets + credentials

Every pipeline downloads its dataset on first `python main.py` and caches it
under `models/<slug>/data/` (gitignored). Helper functions live in
[`pipeline_utils.py`](../pipeline_utils.py) at the repo root.

**Default behaviour (no env config needed):**
- PhysioNet datasets (ECG-ID, TPEHGDB) — auto-download.
- UCI tabular sources (Parkinsons voice, CTG.xls) — auto-download.
- ICBHI lung-sound — auto-download from the direct mirror.
- Synthetic-only pipelines (`bowel_motility`, `stress_ans`) — generate locally.

**Env-gated datasets** (set in root `.env`):

| Variable | Required by | Get it at |
|---|---|---|
| `KAGGLE_USERNAME` + `KAGGLE_KEY` | `skin_disease`, `retinal_disease`, `retinal_age` | https://www.kaggle.com/settings/account |
| `HF_TOKEN` | `retinal_age` (RETFound weights) | https://huggingface.co/settings/tokens |
| `SYNAPSE_AUTH_TOKEN` | `parkinson_screener` (WearGait gait — voice still works without it) | https://www.synapse.org/Profile:Tokens |
| `MEDVERSE_FETCH_LARGE=true` | `ecg_arrhythmia`, `cardiac_age` (PTB-XL 25 GB), and ISIC 2024 inside `skin_disease` | n/a |
| `WESAD_ROOT` | `stress_ans` (real path; default = synthetic) | https://uni-siegen.de/life/home/ (registration) |

When a credential is missing, the pipeline raises `DatasetUnavailable` with a
clear hint string telling the user exactly which env var to set. No silent
fallbacks.

The full reference of dataset → cache path → auth lives in each pipeline's
own `<slug>/README.md` "Data" section.

## LangGraph tool integration

Every trained pipeline is exposed as a LangChain `@tool` in
[src/utils/model_tools.py](../src/utils/model_tools.py) and registered against
the relevant specialist graph through
[src/utils/utils.py](../src/utils/utils.py)`:EXPERT_TOOLS`:

| Specialist graph | Model tools |
|---|---|
| Cardiology Expert | `predict_ecg_arrhythmia`, `predict_cardiac_age`, `predict_ecg_biometric` |
| Pulmonology Expert | `predict_lung_sound` |
| Neurology Expert | `predict_parkinson` |
| Dermatology Expert | `predict_skin_disease` |
| Obstetrics Expert | `predict_fetal_health`, `predict_preterm_labour` |
| Ocular Expert | `predict_retinal_disease`, `predict_retinal_age` |
| General Physician | (synthesises specialist outputs — no direct ML tool) |

Each tool resolves the latest trained-model artifact via
`registry.trained_model_path(slug)`, projects the live SQLite snapshot into
the pipeline's expected feature columns (per-slug map in
`model_tools._features_for`), runs `ModelEstimator.predict`, and returns a
JSON string the agent can read.

When a pipeline hasn't been trained yet, the tool returns
`{"status": "model_unavailable", "hint": "cd models/<slug> && python main.py"}`
so the graphs degrade gracefully instead of raising.

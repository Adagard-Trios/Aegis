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

```bash
cd models/<pipeline>
python -m src.pipeline.training_pipeline                          # train end-to-end
python -m src.pipeline.batch_prediction --input x.csv --output y.csv
uvicorn app:app --port 8001                                       # serve as microservice
```

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

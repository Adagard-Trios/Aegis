# Retinal Biological Age Model

Self-contained MedVerse model pipeline. Same folder + code structure as every
other pipeline under [models/](../) — see [models/README.md](../README.md) for
the canonical layout and conventions.

## Layout

```
.
├── app.py                   # FastAPI service exposing POST /predict
├── data_schema/schema.yaml  # Input/output schema (TODO)
├── notebooks/source.ipynb   # Source experiment notebook
└── src/
    ├── components/          # data_ingestion, data_validation, data_transformation, model_trainer
    ├── constants/           # paths + hyperparameters
    ├── entity/              # *Config and *Artifact dataclasses per stage
    ├── exception/           # MedVerseException wrapper
    ├── logging/             # rotating file logger
    ├── pipeline/            # TrainingPipeline + BatchPrediction orchestrators
    └── utils/
        ├── main_utils/      # save/load, yaml helpers
        └── ml_utils/        # metric + model estimator
```

## Run

Train end-to-end:

```bash
cd models/retinal_age
python -m src.pipeline.training_pipeline
```

Score a CSV:

```bash
python -m src.pipeline.batch_prediction --input <path.csv> --output <out.csv>
```

Serve as a microservice:

```bash
uvicorn app:app --port 8001 --reload
```

## Source notebook

[`notebooks/source.ipynb`](notebooks/source.ipynb) — port the relevant code from
the notebook into the components below. Each stub raises `NotImplementedError`
until you fill it in.

## Status

Skeleton scaffold — implement the stub methods marked `NotImplementedError` to
make the pipeline runnable end-to-end. The skeleton's logger, exception wrapper,
config/artifact dataclasses, and orchestrator are ready to use as-is.

## Data

- **Dataset:** ODIR-5K (Kaggle `jeftaadriel/oia-odir-dataset`) for fundus images.
- **Auxiliary:** RETFound MAE encoder weights (`rmaphoh/RETFound_MAE` on HuggingFace, file `RETFound_mae_natureCFP.pth`).
- **Auth:** `KAGGLE_USERNAME`, `KAGGLE_KEY`, plus `HF_TOKEN` for the encoder.
- **Size:** 3.5 GB images + 4 GB weights.
- **Cache:** `data/odir/` and `data/retfound/`
- **Auto-download:** yes (when creds set). RETFound is best-effort — pipeline still trains tabular features if HF unavailable.

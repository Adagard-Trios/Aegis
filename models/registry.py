"""Programmatic registry of every model pipeline under this directory.

Lets the runtime adapters in src/ml/ + ops scripts iterate over all pipelines
without hardcoding paths, and gives the FastAPI backend a single source of
truth when surfacing per-model status / weights / FHIR DiagnosticReport
specialty mappings.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class PipelineSpec:
    slug: str               # folder name under models/
    title: str              # human-readable
    domain: str             # clinical specialty
    task: str               # classification | regression | metric_learning
    fhir_specialty: Optional[str] = None  # mapped to /api/fhir/DiagnosticReport/<specialty>


PIPELINES: List[PipelineSpec] = [
    PipelineSpec("ecg_arrhythmia",    "ECG Arrhythmia Analyser",      "cardiology",   "classification", "Cardiology"),
    PipelineSpec("cardiac_age",       "Cardiac Biological Age",       "cardiology",   "regression",     "Cardiology"),
    PipelineSpec("ecg_biometric",     "ECG Biometric Identity",       "cardiology",   "metric_learning", None),
    PipelineSpec("stress_ans",        "Stress / ANS Classifier",      "autonomic",    "classification", "Neurology"),
    PipelineSpec("lung_sound",        "Lung Sound Analyser",          "pulmonary",    "classification", "Pulmonary"),
    PipelineSpec("parkinson_screener","Parkinson Screener",           "neurology",    "classification", "Neurology"),
    PipelineSpec("fetal_health",      "Foetal Health Analyser",       "obstetrics",   "classification", "Obstetrics"),
    PipelineSpec("preterm_labour",    "Preterm Labour Predictor",     "obstetrics",   "classification", "Obstetrics"),
    PipelineSpec("bowel_motility",    "Bowel / GI Motility",          "gi",           "classification", None),
    PipelineSpec("skin_disease",      "Skin Disease Detector",        "dermatology",  "classification", "Dermatology"),
    PipelineSpec("retinal_disease",   "Retinal Disease Classifier",   "ocular",       "classification", "Ocular"),
    PipelineSpec("retinal_age",       "Retinal Biological Age",       "ocular",       "regression",     "Ocular"),
]

_HERE = os.path.dirname(os.path.abspath(__file__))


def root() -> str:
    return _HERE


def by_slug(slug: str) -> PipelineSpec:
    for p in PIPELINES:
        if p.slug == slug:
            return p
    raise KeyError(f"unknown pipeline: {slug}")


def by_domain(domain: str) -> List[PipelineSpec]:
    return [p for p in PIPELINES if p.domain == domain]


def by_specialty(specialty: str) -> List[PipelineSpec]:
    return [p for p in PIPELINES if p.fhir_specialty == specialty]


def folder(slug: str) -> str:
    return os.path.join(_HERE, slug)


def trained_model_path(slug: str) -> Optional[str]:
    """Return the latest trained-model artifact path, or None."""
    import glob
    pattern = os.path.join(_HERE, slug, "artifacts", "*", "model_trainer", "trained_model", "model.pkl")
    matches = sorted(glob.glob(pattern))
    return matches[-1] if matches else None

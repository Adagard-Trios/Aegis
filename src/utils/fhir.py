"""
src/utils/fhir.py

HL7 FHIR R4 serializers for MedVerse telemetry and expert interpretations.

The module emits plain dicts that conform to the FHIR R4 JSON Resource
shape. If the optional `fhir.resources` package is installed, outputs are
additionally validated against the official Pydantic models; otherwise
the raw dicts are returned so the API keeps working.

Primary exports:
  • snapshot_to_observations(snapshot, patient_id)           → list[dict]
  • snapshot_to_bundle(snapshot, patient_id)                 → dict (Bundle)
  • expert_to_diagnostic_report(specialty, finding, ...)     → dict (DiagnosticReport)
  • patient_resource(patient_id, profile)                    → dict (Patient)
  • device_resource(device_name, serial=None)                → dict (Device)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from fhir.resources.observation import Observation as _FObservation
    from fhir.resources.diagnosticreport import DiagnosticReport as _FDiagnosticReport
    from fhir.resources.patient import Patient as _FPatient
    from fhir.resources.device import Device as _FDevice
    from fhir.resources.bundle import Bundle as _FBundle

    _FHIR_AVAILABLE = True
except Exception:  # pragma: no cover
    _FHIR_AVAILABLE = False


# ─── Code system helpers ────────────────────────────────────────────────────

LOINC = "http://loinc.org"
SNOMED = "http://snomed.info/sct"

# Vital-sign LOINC codes
LOINC_CODES: Dict[str, Dict[str, str]] = {
    "heart_rate":      {"code": "8867-4",  "display": "Heart rate",              "unit": "/min"},
    "spo2":            {"code": "59408-5", "display": "Oxygen saturation",        "unit": "%"},
    "breathing_rate":  {"code": "9279-1",  "display": "Respiratory rate",         "unit": "/min"},
    "hrv_rmssd":       {"code": "80404-7", "display": "R-R interval SDNN",        "unit": "ms"},
    "perfusion_index": {"code": "61006-3", "display": "Perfusion index",          "unit": "%"},
    "cervical_temp":   {"code": "8310-5",  "display": "Body temperature",         "unit": "Cel"},
    "left_axilla":     {"code": "8328-7",  "display": "Axillary temp left",       "unit": "Cel"},
    "right_axilla":    {"code": "8328-7",  "display": "Axillary temp right",      "unit": "Cel"},
    "spinal_angle":    {"code": "41950-7", "display": "Posture angle",            "unit": "deg"},
    "contractions":    {"code": "82310-5", "display": "Uterine contractions",     "unit": "{count}"},
    "fetal_hr":        {"code": "55283-6", "display": "Fetal heart rate",         "unit": "/min"},
}

# Specialty → DiagnosticReport LOINC
DR_CODES: Dict[str, Dict[str, str]] = {
    "cardiology":        {"code": "18753-8", "display": "Cardiology study"},
    "pulmonary":         {"code": "18748-8", "display": "Pulmonology study"},
    "neurology":         {"code": "47043-1", "display": "Neurology consultation"},
    "dermatology":       {"code": "34111-5", "display": "Dermatology report"},
    "gynecology":        {"code": "47040-7", "display": "Obstetrics consultation"},
    "ocular":            {"code": "29271-4", "display": "Ophthalmology report"},
    "general_physician": {"code": "11488-4", "display": "Consultation note"},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate(resource_cls, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate via fhir.resources if available; otherwise return data."""
    if not _FHIR_AVAILABLE or resource_cls is None:
        return data
    try:
        obj = resource_cls(**data)
        try:
            return obj.model_dump(mode="json", exclude_none=True)
        except AttributeError:
            return obj.dict(exclude_none=True)
    except Exception as e:
        logger.warning(f"FHIR validation failed for {resource_cls.__name__}: {e}")
        return data


# ─── Observation helpers ────────────────────────────────────────────────────

def _observation(
    code_key: str,
    value: float,
    patient_id: str,
    effective: Optional[str] = None,
    category: str = "vital-signs",
) -> Dict[str, Any]:
    meta = LOINC_CODES.get(code_key)
    if meta is None:
        return {}
    data = {
        "resourceType": "Observation",
        "id": str(uuid.uuid4()),
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": category,
                "display": category.replace("-", " ").title(),
            }],
        }],
        "code": {
            "coding": [{
                "system": LOINC,
                "code": meta["code"],
                "display": meta["display"],
            }],
            "text": meta["display"],
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": effective or _now_iso(),
        "valueQuantity": {
            "value": float(value),
            "unit": meta["unit"],
            "system": "http://unitsofmeasure.org",
            "code": meta["unit"],
        },
    }
    return _validate(_FObservation if _FHIR_AVAILABLE else None, data)


def snapshot_to_observations(
    snapshot: Dict[str, Any],
    patient_id: str = "default_patient",
) -> List[Dict[str, Any]]:
    """Flatten a MedVerse telemetry snapshot into FHIR R4 Observations."""
    observations: List[Dict[str, Any]] = []
    if not snapshot:
        return observations

    effective = _now_iso()

    vitals = snapshot.get("vitals") or {}
    for key in ("heart_rate", "spo2", "breathing_rate", "hrv_rmssd", "perfusion_index"):
        if vitals.get(key):
            obs = _observation(key, vitals[key], patient_id, effective)
            if obs:
                observations.append(obs)

    temps = snapshot.get("temperature") or {}
    if temps.get("cervical"):
        observations.append(_observation("cervical_temp", temps["cervical"], patient_id, effective))
    if temps.get("left_axilla"):
        observations.append(_observation("left_axilla", temps["left_axilla"], patient_id, effective))
    if temps.get("right_axilla"):
        observations.append(_observation("right_axilla", temps["right_axilla"], patient_id, effective))

    imu = snapshot.get("imu") or {}
    if imu.get("spinal_angle") is not None:
        observations.append(_observation("spinal_angle", imu["spinal_angle"], patient_id, effective))

    fetal = snapshot.get("fetal") or {}
    contractions = fetal.get("contractions") or []
    if contractions:
        observations.append(
            _observation("contractions", sum(1 for c in contractions if c), patient_id, effective)
        )

    return [o for o in observations if o]


def snapshot_to_bundle(
    snapshot: Dict[str, Any],
    patient_id: str = "default_patient",
) -> Dict[str, Any]:
    """Pack the Observation list into a FHIR R4 `Bundle` of type `collection`."""
    observations = snapshot_to_observations(snapshot, patient_id)
    bundle = {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "type": "collection",
        "timestamp": _now_iso(),
        "entry": [{"resource": o} for o in observations],
    }
    return _validate(_FBundle if _FHIR_AVAILABLE else None, bundle)


# ─── DiagnosticReport ────────────────────────────────────────────────────────

def expert_to_diagnostic_report(
    specialty: str,
    finding: str,
    severity: str,
    severity_score: float,
    patient_id: str = "default_patient",
    generated_at: Optional[str] = None,
    confidence: float = 0.0,
    recommendations: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Serialize a MedVerse expert interpretation as a FHIR R4 DiagnosticReport."""
    spec_key = specialty.lower().replace(" expert", "").replace(" ", "_")
    code_meta = DR_CODES.get(spec_key, DR_CODES["general_physician"])

    conclusion_parts = [finding]
    if recommendations:
        conclusion_parts.append("\n\nRecommendations:")
        conclusion_parts.extend(f"- {r}" for r in recommendations)

    data = {
        "resourceType": "DiagnosticReport",
        "id": str(uuid.uuid4()),
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                "code": "OTH",
                "display": "Other",
            }],
        }],
        "code": {
            "coding": [{
                "system": LOINC,
                "code": code_meta["code"],
                "display": code_meta["display"],
            }],
            "text": f"MedVerse {specialty} interpretation",
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": generated_at or _now_iso(),
        "issued": _now_iso(),
        "performer": [{"display": f"MedVerse {specialty} AI agent"}],
        "conclusion": "".join(conclusion_parts)[:4000],
        "extension": [
            {
                "url": "http://medverse.ai/fhir/StructureDefinition/severity",
                "valueString": severity,
            },
            {
                "url": "http://medverse.ai/fhir/StructureDefinition/severity-score",
                "valueDecimal": float(severity_score),
            },
            {
                "url": "http://medverse.ai/fhir/StructureDefinition/ai-confidence",
                "valueDecimal": float(confidence),
            },
        ],
    }
    return _validate(_FDiagnosticReport if _FHIR_AVAILABLE else None, data)


# ─── Patient & Device ───────────────────────────────────────────────────────

def patient_resource(
    patient_id: str,
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    p = profile or {}
    data = {
        "resourceType": "Patient",
        "id": patient_id,
        "active": True,
    }
    if p.get("name"):
        data["name"] = [{"text": p["name"]}]
    if p.get("gender"):
        data["gender"] = p["gender"]
    if p.get("birthDate"):
        data["birthDate"] = p["birthDate"]
    return _validate(_FPatient if _FHIR_AVAILABLE else None, data)


def device_resource(device_name: str, serial: Optional[str] = None) -> Dict[str, Any]:
    data = {
        "resourceType": "Device",
        "id": device_name.lower().replace(" ", "-"),
        "status": "active",
        "deviceName": [{"name": device_name, "type": "user-friendly-name"}],
        "manufacturer": "MedVerse",
    }
    if serial:
        data["serialNumber"] = serial
    return _validate(_FDevice if _FHIR_AVAILABLE else None, data)

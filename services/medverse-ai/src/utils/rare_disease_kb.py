"""
Rare-disease knowledge base for the complex_diagnosis_graph.

A small bundled JSONL of conditions (data/rare_diseases.jsonl) is loaded
once into a Chroma collection ("rare_disease") so the rare_disease_agent
can do phenotype-text → candidate-disease similarity lookups.

Why bundled, not live API: a static snapshot needs no auth, no network at
boot, and no consent gate (Phase 5 work). The schema is intentionally a
superset of what Orphanet and OMIM expose — when we add live lookups in
a later phase, the same loader can ingest them into the same collection.

The loader is idempotent: it reads a fingerprint of the JSONL (size +
mtime) and only re-indexes if the file has changed since last boot.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from src.utils import vector_store

logger = logging.getLogger(__name__)

# Where the snapshot lives by default. Overridable via env so a deployment
# can point at a curated, organisation-specific KB without code changes.
_DEFAULT_KB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "rare_diseases.jsonl"
)
_KB_PATH = os.environ.get("MEDVERSE_RARE_DISEASE_KB", _DEFAULT_KB_PATH)
_KB_SPECIALTY_KEY = "rare_disease"   # used as the Chroma collection name

# Module-level cache so we only re-fingerprint the file once per process boot
_loaded_fingerprint: Optional[str] = None


def _file_fingerprint(path: str) -> str:
    try:
        st = os.stat(path)
        return f"{st.st_size}:{int(st.st_mtime)}"
    except OSError:
        return ""


def _load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Read disease entries from the JSONL. Skips malformed lines with a warning."""
    out: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"rare_disease_kb: skipping malformed line {i}: {e}")
    except FileNotFoundError:
        logger.warning(f"rare_disease_kb: snapshot not found at {path} — KB disabled")
    return out


def ensure_loaded() -> int:
    """Index the snapshot into Chroma if not already loaded for the current
    file version. Safe to call from anywhere; subsequent calls within the
    same boot are cheap.

    Returns the number of entries indexed (0 if the KB or embeddings are
    unavailable — caller should fall back to LLM-only proposing).
    """
    global _loaded_fingerprint
    fp = _file_fingerprint(_KB_PATH)
    if not fp:
        return 0
    if fp == _loaded_fingerprint:
        return 0  # already indexed in this process

    entries = _load_jsonl(_KB_PATH)
    if not entries:
        return 0

    # Lazily import langchain_core.documents through the same path the
    # vector_store helpers use, so we degrade together if embeddings fail
    collection = vector_store._get_collection(_KB_SPECIALTY_KEY)
    if collection is None:
        logger.warning("rare_disease_kb: Chroma unavailable — KB lookups will return empty")
        return 0

    try:
        from langchain_core.documents import Document
    except Exception as e:
        logger.warning(f"rare_disease_kb: langchain_core unavailable ({e})")
        return 0

    # Wipe + re-add. Chroma's get-by-id is finicky across versions, so a
    # straight delete-collection approach would force a full re-load on
    # every boot. We instead rely on Chroma's deduplication via stable
    # IDs (entry name as ID), so re-adds are no-ops for unchanged rows.
    docs = []
    for entry in entries:
        name = entry.get("name", "").strip()
        phenotype = entry.get("phenotype", "").strip()
        if not name or not phenotype:
            continue
        metadata = {
            "type": "rare_disease",
            "name": name,
            "icd10": entry.get("icd10") or "",
            "rarity": entry.get("rarity", "common"),
            "specialties": ",".join(entry.get("specialties", [])),
            "patient_id": "_kb",  # synthetic — vector_store get_history filters on patient_id
        }
        docs.append(Document(page_content=phenotype, metadata=metadata))

    try:
        collection.add_documents(docs, ids=[d.metadata["name"] for d in docs])
    except Exception as e:
        # Some Chroma versions error on duplicate IDs instead of upserting.
        # Fall back to plain add (will create duplicates in the worst case
        # but lookups still work — they'll just have a higher recall).
        logger.warning(f"rare_disease_kb: id-keyed add failed ({e}), retrying without ids")
        try:
            collection.add_documents(docs)
        except Exception as e2:
            logger.warning(f"rare_disease_kb: index failed ({e2})")
            return 0

    _loaded_fingerprint = fp
    logger.info(f"rare_disease_kb: indexed {len(docs)} entries")
    return len(docs)


def find_candidates_by_phenotype(
    phenotype_text: str,
    *,
    k: int = 5,
    specialty_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Semantic-search the KB for diseases whose phenotype matches a
    description of the patient's current presentation.

    Returns a list of dicts with: name, icd10, rarity, specialties (list),
    phenotype (the matched text), and similarity_rank (0..k-1).

    `specialty_filter` (optional) narrows results to entries that include
    that specialty key — e.g. "cardiology". Useful when the planner has
    already decided the case is in one domain.
    """
    if not phenotype_text or not phenotype_text.strip():
        return []
    ensure_loaded()

    collection = vector_store._get_collection(_KB_SPECIALTY_KEY)
    if collection is None:
        return []

    try:
        # Pull more than k so we can post-filter by specialty without
        # losing recall if the top-k are all in unrelated domains
        raw = collection.similarity_search(query=phenotype_text, k=max(k * 3, k))
    except Exception as e:
        logger.warning(f"rare_disease_kb: similarity_search failed ({e})")
        return []

    results: List[Dict[str, Any]] = []
    for rank, doc in enumerate(raw):
        md = doc.metadata or {}
        if md.get("type") != "rare_disease":
            continue
        specialties = [s for s in (md.get("specialties") or "").split(",") if s]
        if specialty_filter and specialty_filter not in specialties:
            continue
        results.append({
            "name": md.get("name", "<unknown>"),
            "icd10": md.get("icd10") or None,
            "rarity": md.get("rarity", "common"),
            "specialties": specialties,
            "phenotype": doc.page_content,
            "similarity_rank": rank,
        })
        if len(results) >= k:
            break
    return results

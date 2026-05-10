"""
src/utils/vector_store.py

ChromaDB-based history store for expert interpretation summaries.
Uses LangChain + HuggingFace embeddings for semantic search.

NOTE: If sentence-transformers/HuggingFace fails to load (e.g. Python 3.13
compatibility), all functions gracefully degrade to no-ops so the specialty
graphs can still run without the vector store.
"""
from __future__ import annotations

import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ─── Attempt to load embedding dependencies ─────────────────────────────────

_EMBEDDINGS_AVAILABLE = False
_embeddings = None
_embedding_model_name: Optional[str] = None
_collections: Dict[str, Any] = {}
# Where Chroma writes its sqlite + parquet shards. Override with
# CHROMA_PERSIST_DIR when running on a host that has a different
# writable mount (Render's persistent disk lands at /var/medverse/chroma).
_PERSIST_DIR = os.environ.get(
    "CHROMA_PERSIST_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "chroma_data"),
)


def _embedding_suffix() -> str:
    """Short, filesystem-safe tag for the active embedding model — used to
    segregate Chroma collections across model versions (MiniLM vs. BioLORD
    vectors have different dimensionalities)."""
    if not _embedding_model_name:
        return "default"
    return _embedding_model_name.split("/")[-1].lower().replace("-", "_")


def _get_embeddings():
    """
    Load the sentence-embedding model for the Chroma RAG.

    Model selection (in order of preference):
      1. MEDVERSE_EMBEDDING_MODEL env var, if set.
      2. `FremyCompany/BioLORD-2023` — biomedical-domain encoder, materially
         better recall on clinical text than a general-purpose model.
      3. Fallback: `all-MiniLM-L6-v2` — the original general-purpose encoder;
         used if BioLORD fails to load (e.g. no network on first run).
    """
    global _embeddings, _EMBEDDINGS_AVAILABLE
    if _embeddings is not None:
        return _embeddings

    primary = os.environ.get("MEDVERSE_EMBEDDING_MODEL", "FremyCompany/BioLORD-2023")
    fallback = "sentence-transformers/all-MiniLM-L6-v2"

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except Exception as e:
        logger.warning(f"langchain_huggingface not available: {e}. Vector store disabled.")
        _EMBEDDINGS_AVAILABLE = False
        return None

    global _embedding_model_name
    for model_name in (primary, fallback):
        try:
            _embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            _embedding_model_name = model_name
            _EMBEDDINGS_AVAILABLE = True
            logger.info(f"Vector store using embedding model: {model_name}")
            return _embeddings
        except Exception as e:
            logger.warning(f"Embedding model '{model_name}' failed to load: {e}")

    _EMBEDDINGS_AVAILABLE = False
    return None


def _get_collection(specialty: str):
    """Get or create a LangChain Chroma collection for a given specialty."""
    embeddings = _get_embeddings()
    if embeddings is None:
        return None

    key = specialty.lower().replace(" ", "_").replace("/", "_")
    suffix = _embedding_suffix()
    cache_key = f"{key}::{suffix}"
    if cache_key not in _collections:
        try:
            from langchain_chroma import Chroma
            collection_name = f"{key}_history_{suffix}"
            _collections[cache_key] = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=os.path.join(_PERSIST_DIR, f"{key}_{suffix}"),
            )
        except Exception as e:
            logger.warning(f"Failed to create Chroma collection for {specialty}: {e}")
            return None
    return _collections[cache_key]


# ─── Public API ──────────────────────────────────────────────────────────────


def save_interpretation(
    specialty: str,
    patient_id: str,
    interpretation: str,
    summary: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Save an expert interpretation to the vector store.
    Gracefully no-ops if embeddings are not available.
    """
    collection = _get_collection(specialty)
    if collection is None:
        return

    try:
        from langchain_core.documents import Document
        doc_metadata = {
            "specialty": specialty,
            "patient_id": patient_id,
            "type": "interpretation",
            "full_interpretation": interpretation,
            **(metadata or {}),
        }
        doc = Document(page_content=summary, metadata=doc_metadata)
        collection.add_documents([doc])
    except Exception as e:
        logger.warning(f"Failed to save interpretation: {e}")


def get_history(
    specialty: str,
    patient_id: str,
    query: str = "patient health assessment",
    k: int = 5,
) -> List[str]:
    """
    Retrieve the most relevant past interpretations for a patient + specialty.
    Returns empty list if embeddings are not available.
    """
    collection = _get_collection(specialty)
    if collection is None:
        return []

    try:
        results = collection.similarity_search(
            query=query,
            k=k,
            filter={"patient_id": patient_id},
        )
        return [doc.page_content for doc in results]
    except Exception:
        return []


def get_all_history(
    specialty: str,
    query: str = "patient health assessment",
    k: int = 10,
) -> List[str]:
    """
    Retrieve the most relevant past interpretations across all patients.
    Returns empty list if embeddings are not available.
    """
    collection = _get_collection(specialty)
    if collection is None:
        return []

    try:
        results = collection.similarity_search(query=query, k=k)
        return [doc.page_content for doc in results]
    except Exception:
        return []

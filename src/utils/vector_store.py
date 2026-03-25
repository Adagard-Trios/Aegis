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
_collections: Dict[str, Any] = {}
_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_data")


def _get_embeddings():
    global _embeddings, _EMBEDDINGS_AVAILABLE
    if _embeddings is not None:
        return _embeddings
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        _EMBEDDINGS_AVAILABLE = True
        return _embeddings
    except Exception as e:
        logger.warning(f"HuggingFace embeddings not available: {e}. Vector store disabled.")
        _EMBEDDINGS_AVAILABLE = False
        return None


def _get_collection(specialty: str):
    """Get or create a LangChain Chroma collection for a given specialty."""
    embeddings = _get_embeddings()
    if embeddings is None:
        return None

    key = specialty.lower().replace(" ", "_").replace("/", "_")
    if key not in _collections:
        try:
            from langchain_chroma import Chroma
            collection_name = f"{key}_history"
            _collections[key] = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=os.path.join(_PERSIST_DIR, key),
            )
        except Exception as e:
            logger.warning(f"Failed to create Chroma collection for {specialty}: {e}")
            return None
    return _collections[key]


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

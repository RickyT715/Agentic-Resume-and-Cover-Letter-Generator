"""ChromaDB vector store wrapper for the RAG pipeline.

Stores and retrieves company research chunks using embeddings.
Data is persisted to disk for caching across sessions.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_client = None
_collection = None

COLLECTION_NAME = "company_research"
PERSIST_DIR = Path(__file__).parent.parent / "data" / "chromadb"


def _get_collection():
    """Get or create the ChromaDB collection (lazy singleton)."""
    global _client, _collection
    if _collection is not None:
        return _collection

    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
    except ImportError:
        logger.error("chromadb not installed. Run: pip install chromadb")
        raise

    PERSIST_DIR.mkdir(parents=True, exist_ok=True)

    _client = chromadb.PersistentClient(
        path=str(PERSIST_DIR),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info(f"ChromaDB collection '{COLLECTION_NAME}' loaded with {_collection.count()} documents")
    return _collection


def add_documents(
    texts: list[str],
    metadatas: list[dict],
    ids: list[str],
    embeddings: list[list[float]] | None = None,
):
    """Add documents to the vector store.

    Args:
        texts: Document texts.
        metadatas: Metadata dicts for each document.
        ids: Unique document IDs.
        embeddings: Pre-computed embeddings (optional, ChromaDB will compute if None).
    """
    collection = _get_collection()

    kwargs = {
        "documents": texts,
        "metadatas": metadatas,
        "ids": ids,
    }
    if embeddings is not None:
        kwargs["embeddings"] = embeddings

    collection.upsert(**kwargs)
    logger.info(f"Added/updated {len(texts)} documents to vector store")


def query(
    query_text: str,
    n_results: int = 5,
    company_name: Optional[str] = None,
    query_embedding: list[float] | None = None,
) -> list[dict]:
    """Query the vector store for relevant documents.

    Args:
        query_text: The search query.
        n_results: Number of results to return.
        company_name: Optional filter by company name.
        query_embedding: Pre-computed query embedding.

    Returns:
        List of dicts with "text", "metadata", and "distance" keys.
    """
    collection = _get_collection()

    if collection.count() == 0:
        return []

    where = {"company_name": company_name.lower()} if company_name else None

    kwargs = {
        "n_results": min(n_results, collection.count()),
    }
    if query_embedding is not None:
        kwargs["query_embeddings"] = [query_embedding]
    else:
        kwargs["query_texts"] = [query_text]

    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    docs = []
    if results and results["documents"]:
        for i, text in enumerate(results["documents"][0]):
            docs.append({
                "text": text,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0.0,
            })

    return docs


def delete_company(company_name: str) -> int:
    """Delete all documents for a company.

    Args:
        company_name: Company name to delete.

    Returns:
        Number of documents deleted.
    """
    collection = _get_collection()

    # Get IDs for the company
    results = collection.get(
        where={"company_name": company_name.lower()},
    )

    if results and results["ids"]:
        collection.delete(ids=results["ids"])
        count = len(results["ids"])
        logger.info(f"Deleted {count} documents for company '{company_name}'")
        return count

    return 0


def get_company_info(company_name: str) -> list[dict]:
    """Get all stored documents for a company.

    Args:
        company_name: Company name to look up.

    Returns:
        List of document dicts with "text" and "metadata".
    """
    collection = _get_collection()

    results = collection.get(
        where={"company_name": company_name.lower()},
    )

    docs = []
    if results and results["documents"]:
        for i, text in enumerate(results["documents"]):
            docs.append({
                "text": text,
                "metadata": results["metadatas"][i] if results["metadatas"] else {},
            })

    return docs


def list_companies() -> list[str]:
    """List all company names in the vector store."""
    collection = _get_collection()

    if collection.count() == 0:
        return []

    results = collection.get(include=["metadatas"])
    companies = set()
    if results and results["metadatas"]:
        for meta in results["metadatas"]:
            if "company_name" in meta:
                companies.add(meta["company_name"])

    return sorted(companies)

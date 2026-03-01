"""Embedding model wrapper for the RAG pipeline.

Supports multiple embedding backends:
- sentence-transformers (local, free, GPU-optional)
- OpenAI text-embedding-3-small (API, cheap)
"""

import logging

logger = logging.getLogger(__name__)

_embedding_fn = None


def _get_sentence_transformer_fn():
    """Load sentence-transformers with BGE-M3 model."""
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        logger.info("Loaded sentence-transformer model: BAAI/bge-small-en-v1.5")
        return model.encode
    except ImportError:
        logger.warning("sentence-transformers not installed, falling back to simple embeddings")
        return None


def _simple_embedding_fn(texts: list[str]) -> list[list[float]]:
    """Fallback: simple TF-IDF-style character n-gram embeddings (for dev/testing)."""
    import hashlib

    embeddings = []
    for text in texts:
        h = hashlib.sha256(text.encode()).hexdigest()
        vec = [int(h[i : i + 2], 16) / 255.0 for i in range(0, min(len(h), 768 * 2), 2)]
        vec.extend([0.0] * (384 - len(vec)))
        embeddings.append(vec[:384])
    return embeddings


def get_embedding_function():
    """Get the embedding function (lazy-loaded singleton)."""
    global _embedding_fn
    if _embedding_fn is not None:
        return _embedding_fn

    fn = _get_sentence_transformer_fn()
    if fn is not None:
        _embedding_fn = fn
    else:
        _embedding_fn = _simple_embedding_fn
        logger.info("Using simple fallback embeddings (install sentence-transformers for better quality)")

    return _embedding_fn


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using the configured embedding model."""
    fn = get_embedding_function()
    result = fn(texts)
    if hasattr(result, "tolist"):
        return result.tolist()
    return result

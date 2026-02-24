"""Text chunking utilities for the RAG pipeline.

Splits scraped text into smaller, overlapping chunks suitable for
embedding and retrieval.
"""

import logging
import re

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 75,
    separators: list[str] | None = None,
) -> list[str]:
    """Split text into overlapping chunks using recursive character splitting.

    Args:
        text: The text to split.
        chunk_size: Target chunk size in characters.
        chunk_overlap: Number of overlapping characters between chunks.
        separators: Ordered list of separators to try (default: paragraphs, sentences, words).

    Returns:
        List of text chunks.
    """
    if not text or not text.strip():
        return []

    if separators is None:
        separators = ["\n\n", "\n", ". ", ", ", " "]

    chunks = _recursive_split(text.strip(), chunk_size, separators)

    # Add overlap between chunks
    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                prev_tail = chunks[i - 1][-chunk_overlap:]
                chunk = prev_tail + chunk
            overlapped.append(chunk.strip())
        chunks = overlapped

    # Filter out very short chunks
    chunks = [c for c in chunks if len(c) > 20]

    logger.debug(f"Split text ({len(text)} chars) into {len(chunks)} chunks")
    return chunks


def _recursive_split(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    """Recursively split text using the first separator that produces valid chunks."""
    if len(text) <= chunk_size:
        return [text]

    for sep in separators:
        parts = text.split(sep)
        if len(parts) > 1:
            chunks = []
            current = ""
            for part in parts:
                candidate = current + sep + part if current else part
                if len(candidate) > chunk_size and current:
                    chunks.append(current.strip())
                    current = part
                else:
                    current = candidate
            if current.strip():
                chunks.append(current.strip())
            if len(chunks) > 1:
                return chunks

    # Last resort: hard split by chunk_size
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def prepare_chunks_with_metadata(
    chunks: list[str],
    source_url: str,
    company_name: str,
    content_type: str = "general",
) -> list[dict]:
    """Attach metadata to each chunk for vector store indexing.

    Args:
        chunks: List of text chunks.
        source_url: URL the content was scraped from.
        company_name: Normalized company name.
        content_type: Type of content (e.g., "about", "careers", "tech_blog").

    Returns:
        List of dicts with "text" and "metadata" keys.
    """
    from datetime import datetime

    results = []
    for i, chunk in enumerate(chunks):
        results.append({
            "text": chunk,
            "metadata": {
                "source_url": source_url,
                "company_name": company_name.lower(),
                "content_type": content_type,
                "chunk_index": i,
                "scraped_date": datetime.utcnow().isoformat(),
            },
        })
    return results

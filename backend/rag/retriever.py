"""Corrective RAG retriever with relevance grading.

Implements: retrieve -> grade relevance -> optionally rewrite query -> retrieve again.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Relevance threshold for grading retrieved documents
RELEVANCE_THRESHOLD = 0.6  # ChromaDB cosine distance (lower = more similar)


def _grade_relevance(results: list[dict], threshold: float = RELEVANCE_THRESHOLD) -> tuple[list[dict], list[dict]]:
    """Grade retrieved documents by relevance.

    Args:
        results: List of retrieval results with "distance" field.
        threshold: Maximum distance to consider relevant.

    Returns:
        Tuple of (relevant_docs, irrelevant_docs).
    """
    relevant = []
    irrelevant = []
    for doc in results:
        if doc.get("distance", 1.0) <= threshold:
            relevant.append(doc)
        else:
            irrelevant.append(doc)
    return relevant, irrelevant


def _rewrite_query(original_query: str, context: str = "") -> str:
    """Rewrite a query to improve retrieval quality.

    Simple heuristic: extract key terms and reformulate.
    """
    # Extract important words (naive approach - good enough without LLM)
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "shall",
        "for", "and", "nor", "but", "or", "yet", "so", "at", "by",
        "from", "in", "into", "of", "on", "to", "with", "about",
        "that", "this", "these", "those", "it", "its", "what", "which",
    }

    words = original_query.lower().split()
    key_terms = [w for w in words if w not in stop_words and len(w) > 2]

    if context:
        return f"{' '.join(key_terms)} {context}"
    return " ".join(key_terms)


async def retrieve_company_context(
    job_description: str,
    company_name: Optional[str] = None,
    max_results: int = 5,
    max_retries: int = 1,
) -> Optional[str]:
    """Retrieve relevant company context using corrective RAG.

    Args:
        job_description: The job description to use as query.
        company_name: Optional company name to filter by.
        max_results: Maximum number of chunks to retrieve.
        max_retries: Maximum query rewrite retries.

    Returns:
        Formatted company context string, or None if no relevant data.
    """
    from rag.vector_store import query

    # Initial retrieval
    query_text = f"company information culture tech stack values {job_description[:500]}"
    results = query(
        query_text=query_text,
        n_results=max_results,
        company_name=company_name,
    )

    if not results:
        logger.info(f"No company data found for query (company={company_name})")
        return None

    # Grade relevance
    relevant, irrelevant = _grade_relevance(results)

    # Corrective: if too few relevant results, rewrite and retry
    retries = 0
    while len(relevant) < 2 and retries < max_retries:
        retries += 1
        rewritten = _rewrite_query(query_text, company_name or "")
        logger.info(f"Rewriting query (attempt {retries}): {rewritten[:100]}")

        results = query(
            query_text=rewritten,
            n_results=max_results,
            company_name=company_name,
        )
        new_relevant, _ = _grade_relevance(results)
        relevant.extend(new_relevant)
        # Deduplicate
        seen = set()
        unique = []
        for doc in relevant:
            key = doc["text"][:100]
            if key not in seen:
                seen.add(key)
                unique.append(doc)
        relevant = unique

    if not relevant:
        logger.info("No relevant company context found after retrieval")
        return None

    # Format into context string
    context_parts = []
    for doc in relevant[:max_results]:
        source = doc.get("metadata", {}).get("content_type", "general")
        context_parts.append(f"[Source: {source}]\n{doc['text']}")

    context = "\n\n---\n\n".join(context_parts)
    logger.info(f"Retrieved {len(relevant)} relevant company context chunks ({len(context)} chars)")
    return context


async def scrape_and_index_company(company_url: str, company_name: str) -> dict:
    """Scrape a company website and index it in the vector store.

    Args:
        company_url: Base URL to scrape.
        company_name: Company name for indexing.

    Returns:
        Dict with scraping results summary.
    """
    import hashlib

    from rag.chunker import chunk_text, prepare_chunks_with_metadata
    from rag.embeddings import embed_texts
    from rag.scraper import scrape_company
    from rag.vector_store import add_documents

    # Scrape
    pages = await scrape_company(company_url)
    if not pages:
        return {"status": "no_content", "pages_scraped": 0, "chunks_indexed": 0}

    # Chunk and index
    all_chunks = []
    for page in pages:
        chunks = chunk_text(page["text"], chunk_size=500, chunk_overlap=75)
        prepared = prepare_chunks_with_metadata(
            chunks=chunks,
            source_url=page["url"],
            company_name=company_name,
            content_type=page["content_type"],
        )
        all_chunks.extend(prepared)

    if not all_chunks:
        return {"status": "no_chunks", "pages_scraped": len(pages), "chunks_indexed": 0}

    # Generate IDs and embeddings
    texts = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]
    ids = [
        hashlib.sha256(f"{company_name}:{c['metadata']['source_url']}:{c['metadata']['chunk_index']}".encode()).hexdigest()[:16]
        for c in all_chunks
    ]

    try:
        embeddings = embed_texts(texts)
        add_documents(texts=texts, metadatas=metadatas, ids=ids, embeddings=embeddings)
    except Exception as e:
        logger.warning(f"Embedding failed, indexing without embeddings: {e}")
        add_documents(texts=texts, metadatas=metadatas, ids=ids)

    result = {
        "status": "success",
        "pages_scraped": len(pages),
        "chunks_indexed": len(all_chunks),
        "company_name": company_name,
    }
    logger.info(f"Indexed company '{company_name}': {result}")
    return result

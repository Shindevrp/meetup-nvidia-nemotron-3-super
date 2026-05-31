from __future__ import annotations

from functools import lru_cache
from typing import List, Optional, Tuple

from sentence_transformers import SentenceTransformer

from rag.embedder import get_chroma_collection, get_embedding_model

TOP_K = 5


@lru_cache(maxsize=256)
def _cached_retrieve(query: str) -> Tuple[Tuple[str, ...], ...]:
    model = get_embedding_model()
    collection = get_chroma_collection()
    query_embedding = model.encode([query], normalize_embeddings=True).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []
    distances = results["distances"][0] if results["distances"] else []

    scored = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        meta_tuple = tuple(sorted(meta.items()))
        scored.append((doc, meta_tuple, round(1.0 - dist, 2)))

    return tuple(scored)


def retrieve(
    query: str,
    model: Optional[SentenceTransformer] = None,
    top_k: int = TOP_K,
) -> List[Tuple[str, dict, float]]:
    if model is not None:
        return _uncached_retrieve(query, model, top_k)
    cached = _cached_retrieve(query)
    result = []
    for doc, meta_tuple, score in cached:
        meta = dict(meta_tuple)
        result.append((doc, meta, score))
    return result


def _uncached_retrieve(
    query: str,
    model: SentenceTransformer,
    top_k: int,
) -> List[Tuple[str, dict, float]]:
    collection = get_chroma_collection()
    query_embedding = model.encode([query], normalize_embeddings=True).tolist()[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []
    distances = results["distances"][0] if results["distances"] else []
    scored = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        scored.append((doc, meta, round(1.0 - dist, 2)))
    return scored


def clear_retrieve_cache():
    _cached_retrieve.cache_clear()


def format_context(scored_chunks: List[Tuple[str, dict, float]]) -> str:
    lines = []
    for doc, meta, score in scored_chunks:
        lines.append(f"[Source: {meta['name']} | {meta['type']} | Confidence: {score:.2f}]")
        lines.append(doc)
        lines.append("---")
    return "\n".join(lines)

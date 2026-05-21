# Retrieval: takes a user query, embeds it, searches ChromaDB, and returns
# scored chunks with metadata for grounding the LLM response

from typing import List, Tuple

from sentence_transformers import SentenceTransformer

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rag.embedder import get_chroma_collection, get_embedding_model

TOP_K = 5


def retrieve(query: str, model: SentenceTransformer = None, top_k: int = TOP_K) -> List[Tuple[str, dict, float]]:
    """Embed the query, search ChromaDB, return top-k (document, metadata, score) tuples.
    Score is 1.0 - cosine distance (higher = more relevant)."""
    if model is None:
        model = get_embedding_model()

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
        score = 1.0 - dist
        scored.append((doc, meta, score))

    return scored


def format_context(scored_chunks: List[Tuple[str, dict, float]]) -> str:
    """Format retrieved chunks into a readable context string with source labels
    for injection into the LLM prompt."""
    lines = []
    for doc, meta, score in scored_chunks:
        lines.append(f"[Source: {meta['name']} | {meta['type']} | Confidence: {score:.2f}]")
        lines.append(doc)
        lines.append("---")
    return "\n".join(lines)

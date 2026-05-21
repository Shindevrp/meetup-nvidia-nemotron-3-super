from typing import List, Tuple

from sentence_transformers import SentenceTransformer

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rag.embedder import get_chroma_collection, get_embedding_model

TOP_K = 5


def retrieve(query: str, model: SentenceTransformer = None, top_k: int = TOP_K) -> List[Tuple[str, dict, float]]:
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
        score = 1.0 - dist  # convert distance to similarity score
        scored.append((doc, meta, score))

    return scored


def format_context(scored_chunks: List[Tuple[str, dict, float]]) -> str:
    lines = []
    for doc, meta, score in scored_chunks:
        lines.append(f"[Source: {meta['name']} | {meta['type']} | Confidence: {score:.2f}]")
        lines.append(doc)
        lines.append("---")
    return "\n".join(lines)

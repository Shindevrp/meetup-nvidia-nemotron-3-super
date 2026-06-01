from __future__ import annotations

import json
import os
from typing import List, Optional, Tuple

from sentence_transformers import SentenceTransformer

SCHEMES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "schemes")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION_NAME = "schemes"
EMBED_MODEL = "intfloat/multilingual-e5-small"

_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def get_chroma_collection():
    import chromadb
    from chromadb.config import Settings
    client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(name=COLLECTION_NAME)


def chunk_scheme_data(schemes_dir: str) -> Tuple[List[str], List[dict], List[str]]:
    chunks, metadatas, ids = [], [], []
    for fname in os.listdir(schemes_dir):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(schemes_dir, fname), "r", encoding="utf-8") as f:
            data = json.load(f)
        scheme_id = data["id"]

        chunks.append(data["summary"])
        metadatas.append({"scheme_id": scheme_id, "type": "summary", "name": data["name"]})
        ids.append(f"{scheme_id}_summary")

        for i, b in enumerate(data.get("benefits", [])):
            chunks.append(b)
            metadatas.append({"scheme_id": scheme_id, "type": "benefit", "name": data["name"]})
            ids.append(f"{scheme_id}_benefit_{i}")

        el = data.get("eligibility", {})
        for key in ("who_can_apply", "who_cannot_apply", "documents_required"):
            for j, item in enumerate(el.get(key, [])):
                chunks.append(item)
                metadatas.append({"scheme_id": scheme_id, "type": f"eligibility_{key}", "name": data["name"]})
                ids.append(f"{scheme_id}_{key}_{j}")

        ap = data.get("application_process", {})
        how_to = ap.get("how_to_apply", [])
        if isinstance(how_to, list):
            for j, item in enumerate(how_to):
                chunks.append(item)
                metadatas.append({"scheme_id": scheme_id, "type": "process_how_to_apply", "name": data["name"]})
                ids.append(f"{scheme_id}_how_to_apply_{j}")
        elif isinstance(how_to, str):
            chunks.append(how_to)
            metadatas.append({"scheme_id": scheme_id, "type": "process_how_to_apply", "name": data["name"]})
            ids.append(f"{scheme_id}_how_to_apply_0")

        for extra_key in ("if_not_included", "what_to_do_if_rejected", "steps"):
            for j, item in enumerate(ap.get(extra_key, [])):
                chunks.append(item)
                metadatas.append({"scheme_id": scheme_id, "type": f"process_{extra_key}", "name": data["name"]})
                ids.append(f"{scheme_id}_{extra_key}_{j}")

        for faq in data.get("faq", []):
            chunks.append(f"Q: {faq['q']} A: {faq['a']}")
            metadatas.append({"scheme_id": scheme_id, "type": "faq", "name": data["name"]})
            ids.append(f"{scheme_id}_faq_{faq['q'][:30]}")

    return chunks, metadatas, ids


def embed_and_store():
    model = get_embedding_model()
    collection = get_chroma_collection()
    chunks, metadatas, ids = chunk_scheme_data(SCHEMES_DIR)
    embeddings = model.encode(chunks, normalize_embeddings=True).tolist()

    count = collection.count()
    if count > 0:
        return collection

    collection.add(embeddings=embeddings, documents=chunks, metadatas=metadatas, ids=ids)
    return collection


def delete_and_reindex():
    try:
        collection = get_chroma_collection()
        count = collection.count()
        if count > 0:
            collection.delete(ids=collection.get()["ids"])
    except Exception:
        pass
    import shutil
    if os.path.isdir(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR, ignore_errors=True)
    return embed_and_store()

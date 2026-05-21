import json
import os

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

SCHEMES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "schemes")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION_NAME = "schemes"
EMBED_MODEL = "intfloat/multilingual-e5-small"


def get_embedding_model():
    return SentenceTransformer(EMBED_MODEL)


def get_chroma_collection():
    client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(name=COLLECTION_NAME)


def chunk_scheme_data(schemes_dir: str):
    chunks = []
    metadatas = []
    ids = []

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

        for key in ("who_can_apply", "who_cannot_apply", "documents_required"):
            for j, item in enumerate(data.get("eligibility", {}).get(key, [])):
                chunks.append(item)
                metadatas.append({"scheme_id": scheme_id, "type": f"eligibility_{key}", "name": data["name"]})
                ids.append(f"{scheme_id}_{key}_{j}")

        for key in ("how_to_apply",):
            val = data.get("application_process", {}).get(key, [])
            if isinstance(val, list):
                for j, item in enumerate(val):
                    chunks.append(item)
                    metadatas.append({"scheme_id": scheme_id, "type": f"process_{key}", "name": data["name"]})
                    ids.append(f"{scheme_id}_{key}_{j}")
            elif isinstance(val, str):
                chunks.append(val)
                metadatas.append({"scheme_id": scheme_id, "type": f"process_{key}", "name": data["name"]})
                ids.append(f"{scheme_id}_{key}_0")

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
        print(f"  Collection already has {count} chunks — skipping indexing.")
        print("  Delete chroma_db/ directory to re-index.")
        return collection

    collection.add(
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
        ids=ids,
    )
    print(f"Stored {len(chunks)} chunks in ChromaDB")
    return collection

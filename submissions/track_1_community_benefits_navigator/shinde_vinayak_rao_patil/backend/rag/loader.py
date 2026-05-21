import json
import os

from ..rag.embedder import embed_and_store


def load_and_index():
    print("Indexing scheme documents into ChromaDB...")
    embed_and_store()
    print("Done.")

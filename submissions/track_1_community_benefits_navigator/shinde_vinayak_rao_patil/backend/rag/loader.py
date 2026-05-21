# Loader: entry point for indexing scheme documents into ChromaDB at startup

import json
import os

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rag.embedder import embed_and_store


def load_and_index():
    print("Indexing scheme documents into ChromaDB...")
    embed_and_store()
    print("Done.")

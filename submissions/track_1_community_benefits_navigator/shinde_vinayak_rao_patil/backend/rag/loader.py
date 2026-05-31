import logging

from rag.embedder import embed_and_store

logger = logging.getLogger(__name__)


def load_and_index():
    logger.info("Indexing scheme documents into ChromaDB...")
    embed_and_store()
    logger.info("Done indexing.")

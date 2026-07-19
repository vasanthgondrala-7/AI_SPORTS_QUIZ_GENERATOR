import os
import json
import sys
from typing import List

try:
    # Optional fallback for sqlite issues on some Windows setups
    import pysqlite3  # type: ignore
    sys.modules['sqlite3'] = pysqlite3
except Exception:
    pass

from src.config import CHROMA_DB_PATH, MAX_DB_RESULTS, MOCK_MODE

# chromadb is an optional heavy dependency. Import lazily and provide stubs when in MOCK_MODE.
try:
    import chromadb
    from chromadb.utils import embedding_functions
    HAS_CHROMADB = True
except Exception:
    chromadb = None  # type: ignore
    embedding_functions = None  # type: ignore
    HAS_CHROMADB = False


def get_chroma_client():
    """Initializes and returns a persistent ChromaDB client."""
    if not HAS_CHROMADB:
        raise RuntimeError("ChromaDB is not available in this environment")
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


def setup_and_populate_db(json_file_path: str = "./data/sports_facts.json"):
    if not HAS_CHROMADB:
        print("[INFO] ChromaDB not installed — skipping DB setup (MOCK mode).")
        return None

    client = get_chroma_client()
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_or_create_collection(
        name="sports_history",
        embedding_function=embedding_fn,
    )

    # Skip if already has data
    try:
        if collection.count() > 0:
            print(f"ChromaDB already has {collection.count()} items.")
            return collection
    except Exception:
        # older chroma versions may not implement count
        pass

    if not os.path.exists(json_file_path):
        print(f"Data file not found: {json_file_path}")
        return collection

    with open(json_file_path, "r", encoding="utf-8") as fh:
        facts = json.load(fh)

    documents = [item["fact"] for item in facts]
    metadatas = [{"sport": item["sport"]} for item in facts]
    ids = [f"fact_{i}" for i in range(len(documents))]

    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print(f"Added {len(documents)} facts to ChromaDB.")
    return collection


def query_historic_facts(sport: str, query_text: str, n_results: int = MAX_DB_RESULTS) -> List[str]:
    if not HAS_CHROMADB:
        # In MOCK mode or when chromadb isn't installed, return empty list so generator relies on mock context.
        return []

    client = get_chroma_client()
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_or_create_collection(
        name="sports_history",
        embedding_function=embedding_fn,
    )

    try:
        results = collection.query(query_texts=[query_text], n_results=n_results, where={"sport": sport})
        docs = results.get("documents", [[]])[0]
        return docs
    except Exception as e:
        print(f"ChromaDB query failed: {e}")
        return []

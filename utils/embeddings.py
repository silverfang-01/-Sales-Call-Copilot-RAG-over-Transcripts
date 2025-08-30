import chromadb
from chromadb.utils import embedding_functions

def get_collection(persist_dir: str = "data/chroma", name: str = "calls"):
    client = chromadb.PersistentClient(path=persist_dir)
    ef = embedding_functions.DefaultEmbeddingFunction()  # no API needed
    return client.get_or_create_collection(name=name, embedding_function=ef, metadata={"hnsw:space":"cosine"})

def upsert_chunks(coll, chunks: list[dict]) -> int:
    if not chunks: return 0
    coll.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["meta"] for c in chunks],
    )
    return len(chunks)

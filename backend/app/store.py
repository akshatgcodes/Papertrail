"""Chroma, through LangChain: one vector per passage, tagged with its document and
collection so a question can be limited to either."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma

from app.config import settings
from app.embeddings import get_embeddings


@dataclass
class Hit:
    chunk_id: int
    document_id: int
    score: float  # cosine similarity, higher is closer


@lru_cache
def get_store() -> Chroma:
    return Chroma(
        collection_name="passages",
        embedding_function=get_embeddings(),
        persist_directory=str(Path(settings.data_dir) / "chroma"),
        # Cosine distance, so 1 - distance is the similarity the thresholds talk about
        collection_metadata={"hnsw:space": "cosine"},
    )


def add(items: list[tuple[int, int, str, str]]) -> None:
    """items: (chunk_id, document_id, collection, text to embed)"""
    if not items:
        return
    get_store().add_texts(
        texts=[text for *_, text in items],
        metadatas=[{"document_id": d, "collection": c} for _, d, c, _ in items],
        ids=[str(cid) for cid, *_ in items],
    )


def where(document_ids: list[int] | None = None, collection: str | None = None) -> dict | None:
    if document_ids:
        return {"document_id": {"$in": document_ids}}
    if collection:
        return {"collection": collection}
    return None


def search(query: str, k: int, flt: dict | None = None) -> list[Hit]:
    results = get_store().similarity_search_with_score(query, k=k, filter=flt)
    return [
        Hit(int(doc.id), int(doc.metadata["document_id"]), round(1 - distance, 4))
        for doc, distance in results
    ]


def vectors(chunk_ids: list[int]) -> dict[int, list[float]]:
    if not chunk_ids:
        return {}
    got = get_store().get(ids=[str(c) for c in chunk_ids], include=["embeddings"])
    # Chroma returns numpy arrays; plain floats keep the maths and the JSON simple
    return {
        int(i): [float(x) for x in v] for i, v in zip(got["ids"], got["embeddings"], strict=True)
    }


def set_collection(chunk_ids: list[int], document_id: int, collection: str) -> None:
    if chunk_ids:
        meta = {"document_id": document_id, "collection": collection}
        get_store()._collection.update(
            ids=[str(c) for c in chunk_ids], metadatas=[meta] * len(chunk_ids)
        )


def remove(chunk_ids: list[int]) -> None:
    if chunk_ids:
        get_store().delete(ids=[str(c) for c in chunk_ids])

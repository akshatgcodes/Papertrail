"""pgvector backend for app/store.py, for hosts without a persistent disk: vectors live
in the same Postgres database as everything else. Same functions, same scores (cosine
similarity), so retrieval doesn't know which backend it's using."""

from functools import lru_cache

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, MetaData, String, Table, delete, select, text, update

from app.db import engine
from app.embeddings import get_embeddings

metadata = MetaData()

# No dimension on the column: it follows whatever the embedding model returns
vectors_table = Table(
    "passage_vectors",
    metadata,
    Column("chunk_id", Integer, primary_key=True),
    Column("document_id", Integer, nullable=False, index=True),
    Column("collection", String(80), nullable=False, index=True),
    Column("embedding", Vector(), nullable=False),
)


@lru_cache
def init() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    metadata.create_all(engine)


def add(items: list[tuple[int, int, str, str]]) -> None:
    init()
    vecs = get_embeddings().embed_documents([t for *_, t in items])
    rows = [
        {"chunk_id": c, "document_id": d, "collection": col, "embedding": v}
        for (c, d, col, _), v in zip(items, vecs, strict=True)
    ]
    with engine.begin() as conn:
        ids = [r["chunk_id"] for r in rows]
        conn.execute(delete(vectors_table).where(vectors_table.c.chunk_id.in_(ids)))
        conn.execute(vectors_table.insert(), rows)


def search(query: str, k: int, flt: dict | None) -> list[tuple[int, int, float]]:
    """(chunk_id, document_id, cosine similarity), closest first."""
    init()
    q = get_embeddings().embed_query(query)
    distance = vectors_table.c.embedding.cosine_distance(q)
    stmt = select(vectors_table.c.chunk_id, vectors_table.c.document_id, distance)
    if flt and "document_id" in flt:
        stmt = stmt.where(vectors_table.c.document_id.in_(flt["document_id"]["$in"]))
    elif flt and "collection" in flt:
        stmt = stmt.where(vectors_table.c.collection == flt["collection"])
    with engine.connect() as conn:
        rows = conn.execute(stmt.order_by(distance).limit(k)).all()
    return [(c, d, round(1 - dist, 4)) for c, d, dist in rows]


def vectors(chunk_ids: list[int]) -> dict[int, list[float]]:
    init()
    stmt = select(vectors_table.c.chunk_id, vectors_table.c.embedding).where(
        vectors_table.c.chunk_id.in_(chunk_ids)
    )
    with engine.connect() as conn:
        return {c: [float(x) for x in v] for c, v in conn.execute(stmt)}


def set_collection(chunk_ids: list[int], collection: str) -> None:
    init()
    with engine.begin() as conn:
        conn.execute(
            update(vectors_table)
            .where(vectors_table.c.chunk_id.in_(chunk_ids))
            .values(collection=collection)
        )


def remove(chunk_ids: list[int]) -> None:
    init()
    with engine.begin() as conn:
        conn.execute(delete(vectors_table).where(vectors_table.c.chunk_id.in_(chunk_ids)))


def reset() -> None:
    init()
    with engine.begin() as conn:
        conn.execute(delete(vectors_table))

"""Find the passages for a question across the whole library (or one collection, or
chosen documents).

1. Vector search returns `candidates` passages by cosine similarity.
2. If even the best is under `min_similarity`, the library doesn't cover the question:
   stop here, no model call.
3. A cross-encoder re-scores the candidates against the question.
4. Walk them in re-ranked order and keep at most `per_doc` passages per document until
   `k` are chosen, so the answer can draw on several documents instead of the longest one.
"""

from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import store
from app.config import settings
from app.models import Chunk, Document
from app.rerank import get_reranker

# Candidates this far under the cut-off are noise even if the re-ranker likes them
CANDIDATE_FLOOR = 0.1


@dataclass
class Source:
    n: int
    chunk_id: int
    document_id: int
    title: str
    kind: str
    heading: str
    page: int | None
    text: str
    score: float  # cosine similarity to the question
    rerank: float  # cross-encoder score (higher is more relevant; not a probability)
    cited: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def embed_text(title: str, heading: str, text: str) -> str:
    """What gets embedded: the passage plus where it sits. "Install" alone says little;
    "Python › Install" says more."""
    return "\n".join(p for p in (title, heading, text) if p)


def level(score: float) -> str:
    if score >= settings.min_similarity + 0.1:
        return "high"
    if score >= settings.min_similarity:
        return "medium"
    return "low"


def retrieve(
    db: Session,
    query: str,
    k: int,
    document_ids: list[int] | None = None,
    collection: str | None = None,
) -> tuple[list[Source], dict]:
    hits = store.search(query, settings.candidates, store.where(document_ids, collection))
    best = max((h.score for h in hits), default=0.0)
    confidence = {"level": level(best), "score": best, "threshold": settings.min_similarity}
    if best < settings.min_similarity:
        return [], confidence

    hits = [h for h in hits if h.score >= settings.min_similarity - CANDIDATE_FLOOR]
    rows = {
        c.id: (c, d)
        for c, d in db.execute(
            select(Chunk, Document)
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.id.in_([h.chunk_id for h in hits]), Document.status == "ready")
        ).all()
    }
    hits = [h for h in hits if h.chunk_id in rows]
    texts = [
        embed_text(rows[h.chunk_id][1].title, rows[h.chunk_id][0].heading, rows[h.chunk_id][0].text)
        for h in hits
    ]
    scores = get_reranker().score(query, texts)
    ranked = sorted(zip(hits, scores, strict=True), key=lambda hs: -hs[1])

    chosen: list[Source] = []
    per_doc: dict[int, int] = {}
    for hit, rr in ranked:
        if per_doc.get(hit.document_id, 0) >= settings.per_doc:
            continue
        per_doc[hit.document_id] = per_doc.get(hit.document_id, 0) + 1
        chunk, doc = rows[hit.chunk_id]
        chosen.append(
            Source(
                n=len(chosen) + 1,
                chunk_id=chunk.id,
                document_id=doc.id,
                title=doc.title,
                kind=doc.kind,
                heading=chunk.heading,
                page=chunk.page,
                text=chunk.text,
                score=hit.score,
                rerank=round(rr, 4),
            )
        )
        if len(chosen) == k:
            break
    return chosen, confidence

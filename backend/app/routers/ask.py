"""POST /api/ask streams Server-Sent Events:

sources    the passages chosen (or none) and the retrieval confidence
token      a piece of the answer as the model writes it
answer     the final answer text (citations normalised), its status and cited numbers
conflicts  disagreements found between the cited documents (after the answer)
notice     something didn't work (model call failed, conflict check skipped)
done       the saved query id and the time taken
"""

import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import answer, conflicts
from app.auth import require_owner
from app.config import settings
from app.db import SessionLocal, get_db
from app.models import Query
from app.retrieval import retrieve

router = APIRouter(prefix="/api", tags=["ask"], dependencies=[Depends(require_owner)])


class AskIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    mode: str = "ask"  # ask | topic
    document_ids: list[int] | None = None
    collection: str | None = None
    check_conflicts: bool = True


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/ask")
def ask(body: AskIn) -> StreamingResponse:
    if body.mode not in ("ask", "topic"):
        raise HTTPException(422, "mode must be ask or topic")
    query = body.query.strip()
    if not query:
        raise HTTPException(422, "Type a question or a topic")
    _, model_name, _ = settings.llm

    def events():
        started = time.perf_counter()
        state = {
            "answer": "",
            "status": "stopped",  # until the answer is in; also what a disconnect leaves
            "conflicts": [],
            "sources": [],
            "confidence": {},
        }

        def steps():
            with SessionLocal() as db:
                k = settings.topic_k if body.mode == "topic" else settings.top_k
                sources, confidence = retrieve(db, query, k, body.document_ids, body.collection)
            state["sources"] = [s.as_dict() for s in sources]
            state["confidence"] = confidence
            yield sse("sources", {"sources": state["sources"], "confidence": confidence})
            if not sources:
                state["status"] = "not_found"
                yield sse("answer", {"answer": "", "status": "not_found", "cited": []})
                return

            parts: list[str] = []
            try:
                for delta in answer.stream(body.mode, query, sources):
                    parts.append(delta)
                    yield sse("token", {"t": delta})
            except answer.GenerationError as e:
                state["status"] = "error"
                yield sse("notice", {"message": str(e)})
                yield sse("answer", {"answer": "", "status": "error", "cited": []})
                return
            text = answer.normalize_citations("".join(parts).strip())
            if not text or answer.DECLINE in text:
                state["status"] = "declined"
                yield sse("answer", {"answer": "", "status": "declined", "cited": []})
                return
            cited = answer.citations(text)
            for s in state["sources"]:
                s["cited"] = s["n"] in cited
            state["answer"], state["status"] = text, "answered"
            yield sse("answer", {"answer": text, "status": "answered", "cited": sorted(cited)})

            if body.check_conflicts:
                pairs = conflicts.find_pairs(sources, cited)
                if pairs:
                    yield sse("checking", {"pairs": len(pairs)})
                    try:
                        state["conflicts"] = conflicts.check(pairs)
                    except answer.GenerationError as e:
                        yield sse("notice", {"message": str(e)})
                yield sse("conflicts", {"items": state["conflicts"], "pairs": len(pairs)})

        try:
            yield from steps()  # returns early when there's nothing more to send
        finally:
            ms = round((time.perf_counter() - started) * 1000)
            # Saved even when the browser leaves mid-answer
            with SessionLocal() as db:
                q = Query(
                    mode=body.mode,
                    text=query,
                    scope={"document_ids": body.document_ids, "collection": body.collection},
                    answer=state["answer"],
                    status=state["status"],
                    sources=state["sources"],
                    conflicts=state["conflicts"],
                    confidence=state["confidence"],
                    model=model_name if state["status"] in ("answered", "declined") else "",
                    ms=ms,
                )
                db.add(q)
                db.commit()
                qid = q.id
        yield sse("done", {"id": qid, "ms": ms})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def query_dict(q: Query, full: bool = True) -> dict:
    out = {
        "id": q.id,
        "mode": q.mode,
        "text": q.text,
        "status": q.status,
        "created_at": q.created_at.isoformat() + "Z",
        "conflict_count": len(q.conflicts or []),
    }
    if full:
        out |= {
            "answer": q.answer,
            "scope": q.scope,
            "sources": q.sources,
            "conflicts": q.conflicts,
            "confidence": q.confidence,
            "model": q.model,
            "ms": q.ms,
        }
    return out


@router.get("/queries")
def list_queries(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Query).order_by(Query.id.desc()).limit(100))
    return [query_dict(q, full=False) for q in rows]


@router.get("/queries/{query_id}")
def get_query(query_id: int, db: Session = Depends(get_db)) -> dict:
    q = db.get(Query, query_id)
    if not q:
        raise HTTPException(404, "Not found")
    return query_dict(q)


@router.delete("/queries/{query_id}", status_code=204)
def delete_query(query_id: int, db: Session = Depends(get_db)) -> None:
    q = db.get(Query, query_id)
    if not q:
        raise HTTPException(404, "Not found")
    db.delete(q)
    db.commit()

"""Turn a stored document into passages and vectors. Runs after the upload request has
returned (FastAPI background task), so the library shows it as "processing" meanwhile."""

import logging
import threading

from app import store
from app.db import SessionLocal
from app.ingest import pdf, text
from app.models import Chunk, Document, utcnow
from app.retrieval import embed_text

log = logging.getLogger("papertrail.ingest")

# One embedding job at a time: the ONNX model is shared and already uses every core
_lock = threading.Lock()
BATCH = 64


def build_chunks(doc: Document) -> list[Chunk]:
    if doc.kind == "pdf":
        with pdf.open_pdf(doc.file.data) as parsed:
            return [
                Chunk(idx=i, page=p.page, rects=p.rects, text=p.text, heading="")
                for i, p in enumerate(pdf.passages(parsed))
            ]
    return [
        Chunk(idx=i, start=p.start, end=p.end, heading=p.heading[:500], text=p.text)
        for i, p in enumerate(text.passages(doc.content, markdown=doc.kind != "text"))
    ]


def index(doc_id: int) -> None:
    """(Re)builds a document's passages and vectors. Marks it ready or failed."""
    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        if doc is None:
            return
        old = [c.id for c in doc.chunks]
        added: list[int] = []
        try:
            chunks = build_chunks(doc)
            if not chunks:
                raise ValueError(
                    "No text found. Scanned PDFs need OCR, which isn't supported."
                    if doc.kind == "pdf"
                    else "No text found."
                )
            with _lock:
                store.remove(old)
                doc.chunks.clear()
                db.flush()
                doc.chunks.extend(chunks)
                db.flush()
                for i in range(0, len(chunks), BATCH):
                    batch = chunks[i : i + BATCH]
                    store.add(
                        [
                            (c.id, doc.id, doc.collection, embed_text(doc.title, c.heading, c.text))
                            for c in batch
                        ]
                    )
                    added += [c.id for c in batch]
            doc.status, doc.error, doc.updated_at = "ready", "", utcnow()
            db.commit()
            log.info("indexed %s (%s): %d passages", doc.title, doc.kind, len(chunks))
        except Exception as e:  # noqa: BLE001 — any failure is shown on the document
            log.exception("indexing %s failed", doc_id)
            db.rollback()
            store.remove(added)
            doc = db.get(Document, doc_id)
            if doc is not None:
                doc.status = "failed"
                doc.error = str(e)[:500] or type(e).__name__
                db.commit()

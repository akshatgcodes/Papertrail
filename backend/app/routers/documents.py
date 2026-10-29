import re
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import store
from app.auth import require_owner
from app.config import settings
from app.db import get_db
from app.ingest import pdf, service, text, web
from app.models import Chunk, Document, utcnow

router = APIRouter(prefix="/api", tags=["documents"], dependencies=[Depends(require_owner)])

TEXT_TYPES = {".md": "markdown", ".markdown": "markdown", ".txt": "text"}


def doc_dict(d: Document, chunks: int | None = None) -> dict:
    return {
        "id": d.id,
        "kind": d.kind,
        "title": d.title,
        "filename": d.filename,
        "source_url": d.source_url,
        "collection": d.collection,
        "pages": d.pages,
        "chars": d.chars,
        "status": d.status,
        "error": d.error,
        "chunks": chunks if chunks is not None else len(d.chunks),
        "created_at": d.created_at.isoformat() + "Z",
        "updated_at": d.updated_at.isoformat() + "Z",
    }


def _collection(name: str | None) -> str:
    name = re.sub(r"\s+", " ", name or "").strip()
    return name[:80] or "General"


def _get(db: Session, doc_id: int) -> Document:
    d = db.get(Document, doc_id)
    if d is None:
        raise HTTPException(404, "Document not found")
    return d


def _queue(db: Session, doc: Document, tasks: BackgroundTasks) -> dict:
    db.add(doc)
    db.commit()
    tasks.add_task(service.index, doc.id)
    return doc_dict(doc, 0)


@router.get("/documents")
def list_documents(
    collection: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    counts = dict(
        db.execute(select(Chunk.document_id, func.count()).group_by(Chunk.document_id)).all()
    )
    stmt = select(Document).order_by(Document.created_at.desc(), Document.id.desc())
    if collection:
        stmt = stmt.where(Document.collection == collection)
    if q:
        stmt = stmt.where(Document.title.ilike(f"%{q.strip()}%"))
    return [doc_dict(d, counts.get(d.id, 0)) for d in db.scalars(stmt)]


@router.get("/collections")
def collections(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(Document.collection, func.count())
        .group_by(Document.collection)
        .order_by(Document.collection)
    ).all()
    return [{"name": name, "documents": n} for name, n in rows]


@router.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    by_kind = dict(db.execute(select(Document.kind, func.count()).group_by(Document.kind)).all())
    return {
        "documents": sum(by_kind.values()),
        "by_kind": by_kind,
        "passages": db.scalar(select(func.count()).select_from(Chunk)),
        "processing": db.scalar(select(func.count()).where(Document.status == "processing")),
        "failed": db.scalar(select(func.count()).where(Document.status == "failed")),
    }


@router.post("/documents/upload", status_code=201)
def upload(
    tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    collection: str = Form(""),
    db: Session = Depends(get_db),
) -> list[dict]:
    """PDF, Markdown or plain-text files, several at once. Each is checked here; the
    slow part (passages and embeddings) happens after the response."""
    limit = settings.max_upload_mb * 1024 * 1024
    # Check every file before saving any, so one bad file doesn't leave the others
    # half-added (background tasks don't run when the request fails)
    ready: list[tuple[Document, bytes | None]] = []
    for f in files:
        name = Path(f.filename or "document").name[:255]
        ext = Path(name).suffix.lower()
        data = f.file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, f"{name}: files up to {settings.max_upload_mb} MB")
        if ext == ".pdf":
            try:
                with pdf.open_pdf(data) as parsed:
                    if parsed.page_count > settings.max_pages:
                        raise HTTPException(413, f"{name}: PDFs up to {settings.max_pages} pages")
                    title, pages = pdf.title_of(parsed, name)[:500], parsed.page_count
            except pdf.PdfError as e:
                raise HTTPException(422, f"{name}: {e}") from e
            doc = Document(kind="pdf", title=title, filename=name, pages=pages, chars=0)
            ready.append((doc, data))
        elif ext in TEXT_TYPES:
            try:
                content = data.decode("utf-8-sig")
            except UnicodeDecodeError as e:
                raise HTTPException(422, f"{name}: not UTF-8 text") from e
            content = content.replace("\r\n", "\n")[: settings.max_chars]
            if not content.strip():
                raise HTTPException(422, f"{name}: the file is empty")
            kind = TEXT_TYPES[ext]
            title = (text.markdown_title(content) if kind == "markdown" else None) or Path(
                name
            ).stem
            doc = Document(
                kind=kind, title=title[:500], filename=name, content=content, chars=len(content)
            )
            ready.append((doc, None))
        else:
            raise HTTPException(415, f"{name}: PDF, Markdown (.md) or text (.txt) only")

    out = []
    for doc, data in ready:
        doc.collection = _collection(collection)
        db.add(doc)
        db.flush()
        if data is not None:
            service.pdf_path(doc.id).write_bytes(data)
        out.append(_queue(db, doc, tasks))
    return out


class UrlIn(BaseModel):
    url: str = Field(min_length=4, max_length=2000)
    collection: str = ""


@router.post("/documents/url", status_code=201)
def add_url(body: UrlIn, tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    url = body.url.strip()
    if "://" not in url:
        url = "https://" + url
    try:
        title, content = web.extract(web.fetch(url), url)
    except web.FetchError as e:
        raise HTTPException(422, str(e)) from e
    if len(content) < 50:
        raise HTTPException(422, "Couldn't find readable text on that page")
    doc = Document(
        kind="url",
        title=title,
        source_url=url,
        content=content,
        chars=len(content),
        collection=_collection(body.collection),
    )
    return _queue(db, doc, tasks)


class NoteIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=200_000)
    collection: str = ""


@router.post("/documents/note", status_code=201)
def add_note(body: NoteIn, tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    content = body.content.replace("\r\n", "\n")
    doc = Document(
        kind="note",
        title=body.title.strip(),
        content=content,
        chars=len(content),
        collection=_collection(body.collection),
    )
    return _queue(db, doc, tasks)


@router.get("/documents/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db)) -> dict:
    d = _get(db, doc_id)
    return doc_dict(d) | {
        "content": d.content,
        "passages": [
            {
                "id": c.id,
                "idx": c.idx,
                "heading": c.heading,
                "start": c.start,
                "end": c.end,
                "page": c.page,
                "text": c.text,
            }
            for c in d.chunks
        ],
    }


class DocPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    collection: str | None = Field(default=None, max_length=80)
    content: str | None = Field(default=None, min_length=1, max_length=200_000)  # notes only


@router.patch("/documents/{doc_id}")
def update_document(
    doc_id: int, body: DocPatch, tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> dict:
    d = _get(db, doc_id)
    data = body.model_dump(exclude_unset=True)
    reindex = False
    if data.get("title") and data["title"].strip() != d.title:
        d.title = data["title"].strip()
        reindex = True  # the title is part of what's embedded
    if "collection" in data:
        d.collection = _collection(data["collection"])
        if not reindex:
            store.set_collection([c.id for c in d.chunks], d.id, d.collection)
    if "content" in data:
        if d.kind != "note":
            raise HTTPException(422, "Only notes can be edited")
        d.content = data["content"].replace("\r\n", "\n")
        d.chars = len(d.content)
        reindex = True
    d.updated_at = utcnow()
    if reindex:
        d.status = "processing"
        tasks.add_task(service.index, d.id)
    db.commit()
    return doc_dict(d)


@router.post("/documents/{doc_id}/reindex", status_code=202)
def reindex(doc_id: int, tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    d = _get(db, doc_id)
    d.status = "processing"
    db.commit()
    tasks.add_task(service.index, d.id)
    return doc_dict(d)


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: int, db: Session = Depends(get_db)) -> Response:
    d = _get(db, doc_id)
    store.remove([c.id for c in d.chunks])
    if d.kind == "pdf":
        service.pdf_path(d.id).unlink(missing_ok=True)
    db.delete(d)
    db.commit()
    return Response(status_code=204)


@router.get("/documents/{doc_id}/pages/{page}.png")
def page_image(
    doc_id: int,
    page: int,
    chunk: int | None = Query(None, description="Highlight this passage's blocks"),
    db: Session = Depends(get_db),
) -> Response:
    d = _get(db, doc_id)
    if d.kind != "pdf" or not 0 <= page < (d.pages or 0):
        raise HTTPException(404, "No such page")
    rects: list[list[float]] = []
    if chunk is not None:
        c = db.get(Chunk, chunk)
        if c is None or c.document_id != doc_id or c.page != page:
            raise HTTPException(404, "That passage isn't on this page")
        rects = c.rects or []
    png = pdf.render_page(str(service.pdf_path(doc_id)), page, rects)
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})

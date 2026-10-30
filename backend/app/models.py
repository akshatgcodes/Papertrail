from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, JsonColumn

KINDS = ("pdf", "markdown", "text", "url", "note")


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(500))
    filename: Mapped[str] = mapped_column(String(255), default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    # Free-form shelf ("Work", "ML papers"); questions can be limited to one
    collection: Mapped[str] = mapped_column(String(80), default="General", index=True)
    # Extracted text for everything except PDFs (those are re-read from PdfFile)
    content: Mapped[str] = mapped_column(Text, default="")
    pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chars: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(12), default="processing")  # ready | failed
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    chunks: Mapped[list["Chunk"]] = relationship(
        cascade="all, delete-orphan", order_by="Chunk.idx", back_populates="document"
    )
    file: Mapped["PdfFile | None"] = relationship(cascade="all, delete-orphan")


class PdfFile(Base):
    """The uploaded PDF itself. In the database rather than on disk, so hosts without a
    persistent disk keep it, and in its own table so listing documents never loads it."""

    __tablename__ = "pdf_files"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    data: Mapped[bytes] = mapped_column(LargeBinary)


class Chunk(Base):
    """A passage. Its vector lives in the vector store under the chunk id; this keeps where
    it sits."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    idx: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str] = mapped_column(String(500), default="")  # "Section › Subsection"
    text: Mapped[str] = mapped_column(Text)
    # Text documents: character offsets into Document.content, for highlighting
    start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # PDFs: 0-based page and [[x0, y0, x1, y1], ...] blocks to highlight
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rects: Mapped[list | None] = mapped_column(JsonColumn, nullable=True)

    document: Mapped[Document] = relationship(back_populates="chunks")


class Query(Base):
    """A question or topic and everything shown for it, so history renders as it was."""

    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(10))  # ask | topic
    text: Mapped[str] = mapped_column(Text)
    scope: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    answer: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="answered")
    sources: Mapped[list] = mapped_column(JsonColumn, default=list)
    conflicts: Mapped[list] = mapped_column(JsonColumn, default=list)
    confidence: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    model: Mapped[str] = mapped_column(String(100), default="")
    ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

import os
import tempfile

# Settings are read at import time, so point everything at throwaway locations first.
# TEST_DATABASE_URL runs the suite on Postgres instead (CI does)
_tmp = tempfile.mkdtemp()
os.environ.update(
    DATABASE_URL=os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_tmp}/test.db",
    DATA_DIR=_tmp,
    APP_PASSWORD="test-pass",
    EMBEDDINGS="hash",  # no model download in tests
    RERANKER="none",
    MIN_SIMILARITY="0.2",  # hash embeddings score lower than real ones
    CONFLICT_SIMILARITY="0.3",
    LLM_API_KEY="",
    GROQ_API_KEY="",
)

import json  # noqa: E402

import pymupdf  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from langchain_core.messages import AIMessage, AIMessageChunk  # noqa: E402

from app import answer, store  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


def make_pdf(pages: list[list[str]], title: str = "") -> bytes:
    doc = pymupdf.open()
    for paragraphs in pages:
        page = doc.new_page()
        y = 72
        for text in paragraphs:
            page.insert_textbox(pymupdf.Rect(72, y, 520, y + 90), text, fontsize=11)
            y += 110
    if title:
        doc.set_metadata({"title": title})
    return doc.tobytes()


class FakeChat:
    """Streams `reply` in small pieces; `invoke` answers the conflict check."""

    def __init__(self, reply: str = "", verdict: dict | None = None, fail: Exception | None = None):
        self.reply = reply
        self.verdict = verdict or {"results": []}
        self.fail = fail
        self.streamed: list = []
        self.invoked: list = []

    def stream(self, messages):
        self.streamed.append(messages)
        if self.fail:
            raise self.fail
        for i in range(0, len(self.reply), 7):
            yield AIMessageChunk(content=self.reply[i : i + 7])

    def invoke(self, messages):
        self.invoked.append(messages)
        return AIMessage(json.dumps(self.verdict))


def events(response) -> list[tuple[str, dict]]:
    out = []
    for frame in response.text.split("\n\n"):
        lines = dict(line.split(": ", 1) for line in frame.splitlines() if ": " in line)
        if "event" in lines:
            out.append((lines["event"], json.loads(lines["data"])))
    return out


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    store.reset()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def owner(client):
    assert client.post("/api/auth/login", json={"password": "test-pass"}).status_code == 200
    return client


@pytest.fixture
def fake_llm(monkeypatch):
    def install(**kw) -> FakeChat:
        fake = FakeChat(**kw)
        monkeypatch.setattr(answer, "chat_model", lambda: fake)
        return fake

    return install


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(
        "app.ingest.web.socket.getaddrinfo", lambda *a, **k: [(0, 0, 0, "", ("93.184.215.14", 0))]
    )


def add_note(owner, title, content, collection=""):
    r = owner.post(
        "/api/documents/note", json={"title": title, "content": content, "collection": collection}
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def library(owner):
    """Two notes that disagree about one fact, plus an unrelated one."""
    a = add_note(
        owner,
        "Python history (wiki)",
        "# Python\n\n## Releases\n\nPython 2 reached end of life on January 1, 2020. Python 3.0 was released in December 2008.",
        "Reference",
    )
    b = add_note(
        owner,
        "My Python notes",
        "# Notes\n\n## Releases\n\nPython 2 reached end of life on January 1, 2015, so avoid it.",
        "Personal",
    )
    c = add_note(
        owner,
        "Bread",
        "Sourdough needs a starter, flour, water and salt. Bake at a high temperature.",
        "Personal",
    )
    return a, b, c

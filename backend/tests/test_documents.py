import io

import pytest

from app import store
from app.ingest import web
from tests.conftest import add_note, make_pdf


def test_login_required(client):
    assert client.get("/api/documents").status_code == 401
    assert client.post("/api/auth/login", json={"password": "nope"}).status_code == 401


def test_note_is_indexed_with_headings(owner):
    doc = add_note(
        owner,
        "Setup",
        "# Setup\n\n## Install\n\nRun the installer.\n\n## Use\n\nOpen the app.",
        "Work",
    )
    full = owner.get(f"/api/documents/{doc['id']}").json()
    assert full["status"] == "ready" and full["collection"] == "Work"
    assert [p["heading"] for p in full["passages"]] == ["Setup › Install", "Setup › Use"]
    p = full["passages"][0]
    assert full["content"][p["start"] : p["end"]] == p["text"]
    assert owner.get("/api/stats").json() == {
        "documents": 1,
        "by_kind": {"note": 1},
        "passages": 2,
        "processing": 0,
        "failed": 0,
    }


def test_upload_markdown_text_and_pdf(owner):
    pdf = make_pdf(
        [
            [
                "Transformers rely on attention instead of recurrence.",
                "A second block of text on page one.",
            ],
            ["The second page talks about positional encodings."],
        ],
        title="Attention paper",
    )
    files = [
        ("files", ("guide.md", b"\xef\xbb\xbfintro\n\n# The Guide\n\nBody text.", "text/markdown")),
        ("files", ("plain.txt", b"# not a heading\r\n\r\nline", "text/plain")),
        ("files", ("paper.pdf", pdf, "application/pdf")),
    ]
    r = owner.post("/api/documents/upload", files=files, data={"collection": "  Reading   list "})
    assert r.status_code == 201, r.text
    md, txt, paper = r.json()
    assert (md["title"], md["kind"]) == ("The Guide", "markdown")
    assert (txt["title"], txt["kind"]) == ("plain", "text")
    assert (paper["title"], paper["pages"]) == ("Attention paper", 2)
    assert {c["name"] for c in owner.get("/api/collections").json()} == {"Reading list"}

    docs = {d["id"]: d for d in owner.get("/api/documents").json()}
    assert all(d["status"] == "ready" and d["chunks"] > 0 for d in docs.values())
    passages = owner.get(f"/api/documents/{paper['id']}").json()["passages"]
    assert {p["page"] for p in passages} == {0, 1}

    page = passages[0]
    img = owner.get(f"/api/documents/{paper['id']}/pages/0.png", params={"chunk": page["id"]})
    assert img.status_code == 200 and img.content[:4] == b"\x89PNG"
    assert owner.get(f"/api/documents/{paper['id']}/pages/5.png").status_code == 404
    assert (
        owner.get(
            f"/api/documents/{paper['id']}/pages/1.png", params={"chunk": page["id"]}
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "name,data,status",
    [
        ("a.docx", b"PK", 415),
        ("a.md", b"\xff\xfe\x00bad", 422),
        ("a.txt", b"   \n", 422),
        ("a.pdf", b"not a pdf", 422),
    ],
)
def test_bad_upload_saves_nothing(owner, name, data, status):
    files = [("files", ("ok.md", b"# Fine\n\nok", "text/markdown")), ("files", (name, data, "x"))]
    assert owner.post("/api/documents/upload", files=files).status_code == status
    assert owner.get("/api/documents").json() == []


def test_upload_size_limit(owner, monkeypatch):
    monkeypatch.setattr("app.routers.documents.settings.max_upload_mb", 0)
    r = owner.post(
        "/api/documents/upload", files=[("files", ("a.md", io.BytesIO(b"x"), "text/markdown"))]
    )
    assert r.status_code == 413


def test_scanned_pdf_fails_with_a_reason(owner):
    r = owner.post(
        "/api/documents/upload", files=[("files", ("blank.pdf", make_pdf([[]]), "application/pdf"))]
    )
    doc = owner.get(f"/api/documents/{r.json()[0]['id']}").json()
    assert doc["status"] == "failed" and "OCR" in doc["error"]


def test_add_url(owner, monkeypatch, public_dns):
    html = (
        "<title>Guide</title><main><h1>Guide</h1><p>"
        + "Useful words about caching. " * 5
        + "</p></main>"
    )
    monkeypatch.setattr(web, "fetch", lambda url: html)
    r = owner.post("/api/documents/url", json={"url": "example.com/guide"})
    assert r.status_code == 201
    assert (r.json()["source_url"], r.json()["title"]) == ("https://example.com/guide", "Guide")

    monkeypatch.setattr(web, "fetch", lambda url: "<p>tiny</p>")
    assert (
        owner.post("/api/documents/url", json={"url": "https://example.com/x"}).status_code == 422
    )
    r = owner.post("/api/documents/url", json={"url": "http://localhost:8000/"})
    assert r.status_code == 422


def test_edit_note_reindexes(owner):
    doc = add_note(owner, "Plan", "First version of the plan.")
    chunk_ids = [p["id"] for p in owner.get(f"/api/documents/{doc['id']}").json()["passages"]]
    r = owner.patch(f"/api/documents/{doc['id']}", json={"content": "Second version, rewritten."})
    assert r.status_code == 200
    full = owner.get(f"/api/documents/{doc['id']}").json()
    assert full["status"] == "ready" and full["passages"][0]["text"] == "Second version, rewritten."
    assert store.vectors(chunk_ids) == {} or set(store.vectors(chunk_ids)) <= {
        p["id"] for p in full["passages"]
    }


def test_only_notes_are_editable(owner):
    r = owner.post(
        "/api/documents/upload", files=[("files", ("a.md", b"# A\n\ntext", "text/markdown"))]
    )
    assert (
        owner.patch(f"/api/documents/{r.json()[0]['id']}", json={"content": "new"}).status_code
        == 422
    )


def test_move_collection_updates_the_index(owner):
    doc = add_note(owner, "Plan", "Quarterly roadmap for the team.", "Work")
    owner.patch(f"/api/documents/{doc['id']}", json={"collection": "Archive"})
    assert [c["name"] for c in owner.get("/api/collections").json()] == ["Archive"]
    assert store.search("roadmap", 5, store.where(collection="Archive"))
    assert store.search("roadmap", 5, store.where(collection="Work")) == []


def test_delete_removes_vectors(owner):
    doc = add_note(owner, "Temp", "Something to forget about soon.")
    ids = [p["id"] for p in owner.get(f"/api/documents/{doc['id']}").json()["passages"]]
    assert owner.delete(f"/api/documents/{doc['id']}").status_code == 204
    assert store.vectors(ids) == {}
    assert owner.get(f"/api/documents/{doc['id']}").status_code == 404


def test_reindex_and_list_filters(owner):
    a = add_note(owner, "Alpha notes", "alpha text", "One")
    add_note(owner, "Beta notes", "beta text", "Two")
    assert owner.post(f"/api/documents/{a['id']}/reindex").status_code == 202
    assert owner.get(f"/api/documents/{a['id']}").json()["status"] == "ready"
    assert [
        d["title"] for d in owner.get("/api/documents", params={"collection": "Two"}).json()
    ] == ["Beta notes"]
    assert [d["title"] for d in owner.get("/api/documents", params={"q": "alp"}).json()] == [
        "Alpha notes"
    ]

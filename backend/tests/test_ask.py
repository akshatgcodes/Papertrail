import pytest

from app import answer, conflicts
from app.db import SessionLocal
from app.retrieval import Source, retrieve
from tests.conftest import add_note, events

ASK = "When did Python 2 reach end of life?"


def ask(owner, query=ASK, **kw):
    r = owner.post("/api/ask", json={"query": query, **kw})
    assert r.status_code == 200, r.text
    return events(r)


def by_name(evs):
    out = {}
    for name, data in evs:
        out.setdefault(name, []).append(data)
    return out


def test_retrieve_spans_documents_and_respects_scope(library, owner):
    wiki, mine, bread = library
    with SessionLocal() as db:
        sources, conf = retrieve(db, ASK, 8)
        assert {s.document_id for s in sources} >= {wiki["id"], mine["id"]}
        assert conf["level"] in ("medium", "high")
        assert sources[0].heading.endswith("Releases")
        only, _ = retrieve(db, ASK, 8, collection="Personal")
        assert wiki["id"] not in {s.document_id for s in only}
        picked, _ = retrieve(db, ASK, 8, document_ids=[wiki["id"]])
        assert {s.document_id for s in picked} == {wiki["id"]}


def test_per_document_cap(owner, monkeypatch):
    long = "\n\n".join(
        f"## Part {i}\n\nCaching rule {i}: cache responses for speed." for i in range(10)
    )
    big = add_note(owner, "Caching handbook", long)
    small = add_note(owner, "Cache tip", "Cache responses close to the user for speed.")
    monkeypatch.setattr("app.retrieval.settings.per_doc", 3)
    with SessionLocal() as db:
        sources, _ = retrieve(db, "how to cache responses for speed", 8)
    counts = {d: sum(s.document_id == d for s in sources) for d in (big["id"], small["id"])}
    assert counts == {big["id"]: 3, small["id"]: 1}
    assert [s.n for s in sources] == [1, 2, 3, 4]


def test_unrelated_question_is_not_found_without_a_model_call(library, owner, fake_llm):
    fake = fake_llm(reply="should not be used")
    ev = by_name(ask(owner, "quantum chromodynamics gluon"))
    assert ev["sources"][0]["sources"] == [] and ev["sources"][0]["confidence"]["level"] == "low"
    assert ev["answer"][0]["status"] == "not_found"
    assert fake.streamed == []
    q = owner.get(f"/api/queries/{ev['done'][0]['id']}").json()
    assert q["status"] == "not_found" and q["model"] == ""


def test_answer_streams_with_citations_and_conflict(library, owner, fake_llm):
    fake = fake_llm(
        reply="Python 2 reached end of life on January 1, 2020 【1】. Your notes say 2015 [2].",
        verdict={
            "results": [
                {
                    "pair": 1,
                    "conflict": True,
                    "topic": "Python 2 end of life",
                    "claim_a": "January 1, 2020",
                    "claim_b": "January 1, 2015",
                    "note": "Two different dates.",
                }
            ]
        },
    )
    evs = ask(owner)
    names = [n for n, _ in evs]
    assert names[0] == "sources" and names[-1] == "done"
    assert names.index("answer") > names.index("token") and "checking" in names
    ev = by_name(evs)
    tokens = "".join(t["t"] for t in ev["token"])
    assert "【1】" in tokens  # streamed raw...
    final = ev["answer"][0]
    assert (
        final["answer"].endswith("2015 [2].") and "[1]" in final["answer"]
    )  # ...normalised at the end
    assert final["cited"] == [1, 2]

    # The prompt numbers the excerpts and names their documents
    prompt = fake.streamed[0][1].content
    assert "[1] " in prompt and "Question: " + ASK in prompt

    items = ev["conflicts"][0]["items"]
    assert len(items) == 1 and items[0]["claim_b"] == "January 1, 2015"
    sources = {s["n"]: s for s in ev["sources"][0]["sources"]}
    assert sources[items[0]["a"]]["document_id"] != sources[items[0]["b"]]["document_id"]

    saved = owner.get(f"/api/queries/{ev['done'][0]['id']}").json()
    assert saved["status"] == "answered" and saved["conflicts"] == items
    assert [s["cited"] for s in saved["sources"]][:2] == [True, True]
    assert owner.get("/api/queries").json()[0]["conflict_count"] == 1


def test_topic_mode_uses_its_prompt(library, owner, fake_llm):
    fake = fake_llm(reply="### Releases\n- Python 3.0 came out in 2008 [1].")
    ev = by_name(ask(owner, "Python releases", mode="topic", check_conflicts=False))
    assert ev["answer"][0]["status"] == "answered" and "conflicts" not in ev
    assert fake.streamed[0][0].content == answer.TOPIC_SYSTEM
    assert "Topic: Python releases" in fake.streamed[0][1].content


def test_decline(library, owner, fake_llm):
    fake_llm(reply=answer.DECLINE)
    ev = by_name(ask(owner))
    assert ev["answer"][0] == {"answer": "", "status": "declined", "cited": []}
    assert "conflicts" not in ev


def test_model_failure_is_a_notice(library, owner, fake_llm):
    fake_llm(fail=RuntimeError("rate limited"))
    ev = by_name(ask(owner))
    assert "rate limited" in ev["notice"][0]["message"]
    assert ev["answer"][0]["status"] == "error"
    assert owner.get(f"/api/queries/{ev['done'][0]['id']}").json()["status"] == "error"


def test_conflict_check_failure_keeps_the_answer(library, owner, fake_llm, monkeypatch):
    fake = fake_llm(reply="2020 [1], but 2015 [2].")
    monkeypatch.setattr(fake, "invoke", lambda m: (_ for _ in ()).throw(RuntimeError("boom")))
    ev = by_name(ask(owner))
    assert ev["answer"][0]["status"] == "answered"
    assert "Conflict check failed" in ev["notice"][0]["message"]
    assert ev["conflicts"][0]["items"] == []


def test_no_key_is_reported(library, owner):
    ev = by_name(ask(owner))
    assert "LLM_API_KEY" in ev["notice"][0]["message"]


def test_bad_requests(owner):
    assert owner.post("/api/ask", json={"query": "x", "mode": "chat"}).status_code == 422
    assert owner.post("/api/ask", json={"query": "   "}).status_code == 422
    assert owner.get("/api/queries/999").status_code == 404


def test_delete_query(library, owner, fake_llm):
    fake_llm(reply=answer.DECLINE)
    qid = by_name(ask(owner))["done"][0]["id"]
    assert owner.delete(f"/api/queries/{qid}").status_code == 204
    assert owner.get("/api/queries").json() == []


# --- units ----------------------------------------------------------------------------


def src(n, doc, chunk=None, text="t"):
    return Source(n, chunk or n, doc, f"Doc {doc}", "note", "", None, text, 0.8, 1.0)


def test_candidate_pairs_only_across_documents_and_spread():
    sources = [src(1, 1), src(2, 1), src(3, 2), src(4, 3)]
    vecs = {1: [1, 0], 2: [1, 0.01], 3: [1, 0.02], 4: [0, 1]}
    pairs = conflicts.candidate_pairs(sources, vecs)
    # 4 is unrelated and 1-2 share a document; 2-3 is closer than 1-3, same two documents
    assert [(p.a.n, p.b.n) for p in pairs] == [(2, 3)]


def test_pair_budget(monkeypatch):
    monkeypatch.setattr("app.conflicts.settings.max_conflict_pairs", 2)
    sources = [src(i, i) for i in range(1, 7)]
    pairs = conflicts.candidate_pairs(sources, {i: [1, i / 100] for i in range(1, 7)})
    assert len(pairs) == 2


def test_parse_ignores_junk():
    pairs = [conflicts.Pair(src(1, 1), src(2, 2), 0.9)]
    raw = 'Sure! {"results": [{"pair": 1, "conflict": true, "topic": "t"}, {"pair": 7, "conflict": true}, {"pair": "x"}]}'
    assert conflicts.parse(raw, pairs) == [
        {"topic": "t", "claim_a": "", "claim_b": "", "note": "", "a": 1, "b": 2, "similarity": 0.9}
    ]
    with pytest.raises(ValueError):
        conflicts.parse("no json", pairs)


def test_citations():
    assert answer.citations("a [1] b [2][4] c [3, 5] d [x]") == {1, 2, 3, 4, 5}
    assert answer.normalize_citations("x 【2†source】 y 【3】") == "x [2] y [3]"


def test_excerpt_labels():
    s = Source(1, 1, 1, "Paper", "pdf", "Intro", 2, "body", 0.8, 1.0)
    assert answer.excerpt(s) == "[1] Paper › Intro (page 3)\nbody"


def test_one_pair_per_document_pair():
    sources = [src(1, 1), src(2, 1), src(3, 2), src(4, 3)]
    vecs = {1: [1, 0], 2: [1, 0.01], 3: [1, 0.02], 4: [1, 0.03]}
    pairs = conflicts.candidate_pairs(sources, vecs)
    docs = [tuple(sorted((p.a.document_id, p.b.document_id))) for p in pairs]
    assert len(docs) == len(set(docs)) == 3


def test_pairs_touch_a_cited_source():
    sources = [src(1, 1), src(2, 2), src(3, 3)]
    vecs = {1: [1, 0], 2: [1, 0.01], 3: [1, 0.02]}
    pairs = conflicts.candidate_pairs(sources, vecs, cited={3})
    assert all(3 in (p.a.n, p.b.n) for p in pairs) and len(pairs) == 2

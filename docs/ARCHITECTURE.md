# Architecture

```
            ┌─────────────────────────── FastAPI ───────────────────────────┐
 upload ──▶ │ documents router ──▶ Postgres (documents)                      │
 url    ──▶ │        │ background task                                       │
 note   ──▶ │        ▼                                                       │
            │ ingest: parse ─▶ passages ─▶ embed (bge-small) ─▶ Chroma       │
            │                      │                                         │
            │                      └──▶ Postgres (passages: text, offsets,   │
            │                                     page, block boxes)         │
            │                                                                │
 question ─▶│ ask router (SSE)                                               │
            │   retrieve: Chroma top 30 ─▶ cut-off ─▶ cross-encoder ─▶       │
            │             per-document cap ─▶ 8 passages (14 for a topic)    │
            │   answer:   LLM stream with [n] citations                      │
            │   conflicts: similar cross-document pairs ─▶ one LLM call      │
            │   save:     Postgres (queries)                                 │
            └────────────────────────────────────────────────────────────────┘
```

## Ingestion

| Kind | How it becomes passages |
|---|---|
| Markdown, notes | Split along headings. Each passage carries its heading path (`Guide › Install › Linux`) and its start and end offsets in the original text, so the document view can highlight it exactly. Paragraphs under one heading are merged up to 1,000 characters; a longer paragraph is split at sentence ends, and each piece starts with the previous piece's last sentence. |
| Text files | Same, without treating `#` lines as headings. |
| PDF | PyMuPDF text blocks in reading order, merged up to 1,000 characters within a page. Blocks under 30 characters (page numbers, running heads, headings) end a passage. Each passage keeps its page and the rectangles of its blocks, used to draw the highlight on the rendered page. |
| URL | Fetched by the server (public addresses only, every redirect checked), then reduced to headings, paragraphs and list items. Navigation, footers, tables, infoboxes, reference markers and sections like *References* and *External links* are dropped. The result is handled like Markdown. |

What gets embedded is `title + heading path + passage text`, so a passage under "Install" in "Python" is found by questions about installing Python.

Indexing runs as a FastAPI background task after the upload request returns, one document at a time (the ONNX model already uses every core). Re-indexing replaces a document's passages and vectors; a failure removes any vectors added for the attempt and marks the document failed with the reason. A restart marks anything left in "processing" as failed.

## Storage

- **Postgres** (SQLite for local development): `documents`, `chunks` (passages), `queries`.
- **Chroma** (on disk, cosine distance): one collection, one vector per passage, id = passage id, metadata `document_id` and `collection`. Scoping a question is a metadata filter. Moving a document to another collection updates the metadata without re-embedding.
- **Uploads**: the original PDF, kept to render pages.

## Retrieval

1. Chroma returns the 30 nearest passages within the scope.
2. If the best cosine similarity is under `MIN_SIMILARITY` (0.68), stop: the answer is "not in your library" and no model is called.
3. Candidates more than 0.1 under the cut-off are dropped; the rest are scored by the cross-encoder against the question.
4. In re-ranked order, take passages until there are 8 (14 in topic mode), skipping a document once it has 3.

The confidence shown with an answer is the best similarity: strong at 0.78 or more, partial from 0.68.

## Answers

The passages go to the model numbered and labelled (`[3] React docs › useEffect (page 2)`). The prompt allows only what the excerpts say, asks for a citation on every sentence or bullet, asks for disagreements to be stated with both sides cited, and allows exactly `NOT_IN_LIBRARY` when no excerpt bears on the question. Topic mode asks for a two-sentence overview and grouped bullets instead.

## Conflict check

After an answer, among the chosen passages:

1. Pair passages from different documents whose embeddings have cosine similarity ≥ `CONFLICT_SIMILARITY` (0.75), where at least one side was cited.
2. Keep the most similar pair per two documents, no passage in more than two pairs, at most `MAX_CONFLICT_PAIRS` (4).
3. Send all pairs in one call; the model returns JSON saying, per pair, whether the two make incompatible claims about the same thing, with the two claims and a one-line note.

## Event stream

`POST /api/ask` answers with Server-Sent Events:

| Event | Data |
|---|---|
| `sources` | the chosen passages (number, document, heading, page, text, scores) and the confidence |
| `token` | a piece of the answer as it's written |
| `answer` | the final text with citations normalised, its status (`answered`, `not_found`, `declined`, `error`), the cited numbers |
| `checking` | how many pairs are being compared |
| `conflicts` | the conflicts found and how many pairs were checked |
| `notice` | something failed without ending the answer (model error, conflict check skipped) |
| `done` | the saved query's id and the time taken |

The query is saved in a `finally` block, so a question the browser abandons halfway is still in History, marked stopped.

## API

| Method | Path | |
|---|---|---|
| POST | `/api/auth/login`, `/api/auth/logout` · GET `/api/auth/me` | session cookie |
| GET | `/api/documents?collection=&q=` | list |
| POST | `/api/documents/upload` (multipart `files`, `collection`) · `/api/documents/url` · `/api/documents/note` | add |
| GET · PATCH · DELETE | `/api/documents/{id}` | full text and passages · title, collection, note text · remove with its vectors |
| POST | `/api/documents/{id}/reindex` | |
| GET | `/api/documents/{id}/pages/{n}.png?chunk=` | a PDF page, optionally with a passage boxed |
| GET | `/api/collections` · `/api/stats` | |
| POST | `/api/ask` | SSE, see above |
| GET · DELETE | `/api/queries`, `/api/queries/{id}` | history |

## Frontend

React Router pages: Ask (`/`), Library, Document (`/d/:id?p=<passage>`), History, saved answer (`/q/:id`). The stream is read with `fetch` and a small SSE parser (EventSource can't POST) and folded into state by one reducer, which the saved-answer page reuses. Answers are rendered from a small Markdown subset into React elements, so citations become buttons and no model output is inserted as HTML.

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>

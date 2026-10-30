<p align="center">
  <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24"
       fill="none" stroke="#b4531c" stroke-width="1.5"
       stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>
    <path d="M14 3v5h5"/>
    <path d="M9 13h6"/>
    <path d="M9 17h4"/>
  </svg>
</p>

<h1 align="center">Papertrail</h1>

<p align="center">
  <strong>A private knowledge base for your PDFs, notes and saved articles. Ask a question and get an answer drawn from all of them at once, with every passage cited, and a warning when two of your documents disagree.</strong>
</p>

<p align="center">
  <a href="https://papertrail.akshatgcodes.in">
    <img src="https://img.shields.io/badge/live_demo-b4531c-b4531c?style=flat-square" alt="Live Demo">
  </a>
  <img src="https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white" alt="LangChain">
  <img src="https://img.shields.io/badge/Chroma-FF6446?style=flat-square" alt="Chroma">
  <img src="https://img.shields.io/badge/license-GPL--3.0-b4531c?style=flat-square" alt="License">
</p>

---

## What is Papertrail?

[DocuChat](https://github.com/akshatgcodes/DocuChat) answers questions about one PDF. Papertrail works over a **library**: dozens of documents of different kinds, searched together.

1. **Add anything.** PDFs, Markdown and text files, web pages by URL, or notes written in the app. Each is split into passages (along headings where there are any), embedded locally and stored in Chroma, tagged with its document and collection.
2. **Ask across all of it.** Vector search finds 30 candidate passages from the whole library, a cross-encoder re-ranks them, and at most three per document go to the model, so one long document can't crowd out the rest. The answer streams in with `[n]` citations; click one to see the exact passage, and open it highlighted in its document (on the PDF page itself for PDFs).
3. **See disagreements.** After the answer, passages from *different* documents that are about the same thing are paired up and checked for claims that can't both be true. "Your notes say Python 2 reached end of life in 2015; Wikipedia says 2020" shows up as a conflict card with both sides.
4. **Or ask about a topic.** "What do I know about attention in transformers?" is not a question. Topic mode pulls more passages and writes a grouped summary of what your documents say, and where they differ.

When nothing in the library is close to the question, Papertrail says so without calling the model at all.

> **Live demo →** [papertrail.akshatgcodes.in](https://papertrail.akshatgcodes.in)
> Log in with the demo password `demo1234`. The free host sleeps when idle, so the first load can take up to a minute.

---

## What you get

- **Library** with collections, drag-and-drop upload (several files at once), URL import and notes; indexing runs in the background and the list updates as it finishes
- **Ask** in two modes, over the whole library, one collection, or documents you pick; answers stream (Server-Sent Events) and can be stopped
- **Sources panel** grouped by document, with cited and uncited passages told apart
- **Conflict cards**: topic, claim A against claim B, which document says which, one sentence on why they can't both be right
- **Document view** with a passage outline; text documents show the passage highlighted in place, PDFs show the page with the passage's blocks boxed
- **History**: every question is saved with its answer, sources and conflicts, at a permalink
- **Notes are editable**; editing, renaming or moving a document updates the index
- **Local embeddings and re-ranking** (fastembed, ONNX on the CPU): no embedding API key, and the same scores every run
- **Any OpenAI-compatible model** for answers: Groq by default, or OpenAI, or a local Ollama

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 19 · TypeScript · Vite · React Router; own SSE parser and answer renderer |
| Backend | FastAPI (StreamingResponse for SSE, background tasks for indexing) · SQLAlchemy |
| Retrieval | Chroma via LangChain · `BAAI/bge-small-en-v1.5` embeddings · `ms-marco-MiniLM-L-6-v2` cross-encoder, both through fastembed |
| Ingestion | PyMuPDF (text blocks with positions) · BeautifulSoup + lxml for web pages |
| Generation | LangChain `ChatOpenAI` against Groq (`openai/gpt-oss-120b`), OpenAI or Ollama |
| Storage | PostgreSQL (or SQLite) for documents, passages and history; Chroma on disk for vectors, or pgvector in Postgres (`VECTOR_STORE=pgvector`) |
| Tooling | uv · pytest · Vitest · ruff · Docker Compose · GitHub Actions |

---

## Run it

```bash
# Everything → http://localhost:5173 (password: papertrail)
GROQ_API_KEY=... docker compose up --build
```

Or without Docker:

```bash
# API → http://localhost:8000/docs
cd backend && uv sync && cp .env.example .env    # set APP_PASSWORD, SESSION_SECRET and LLM_API_KEY
uv run uvicorn main:app --reload

# App → http://localhost:5173
cd frontend && npm install && npm run dev
```

The first upload downloads the two local models (about 150 MB); the Docker image has them built in. More in [docs/SETUP.md](docs/SETUP.md).

---

## Engineering Decisions

**How does it decide the library doesn't cover a question?**
By the best passage's cosine similarity, before any model call. On a 55-document test library (1,935 passages), twelve questions the library covers scored 0.766 to 0.859; eight it doesn't cover (sourdough, the World Cup, Bitcoin…) scored 0.466 to 0.621. The cut-off sits at 0.68, in that gap. Above it the model can still decline if the passages turn out not to answer.

**Why a per-document cap on passages?**
Without it, one long document (the test library has a 105-passage Wikipedia article) can fill every slot for a question that three documents answer. Candidates are re-ranked first, then taken in order, skipping a document once it has three. A question about Python 2's end of life draws on four documents instead of one.

**How does the conflict check stay cheap?**
Asking a model to compare every pair of eight passages is 28 comparisons. Most pairs are about different things and can't contradict each other. So pairs are pre-filtered without a model: different documents, embedding similarity of at least 0.75, at least one side cited in the answer, one pair per two documents, at most four pairs. Those go to the model in one call that returns JSON. The pairing rules came from a real failure: at first the four slots all went to two Wikipedia articles that agreed with each other, and the note that actually disagreed never got checked.

**Why local embeddings instead of OpenAI's?**
The vectors for a library have to be recomputed if the embedding model changes, so the model should be one you control. Retrieval with bge-small and the re-ranker takes about 300–900 ms per question on a laptop CPU, needs no key, and gives the same scores every run, which is what made the similarity cut-off calibratable.

The live demo is the exception: the local model and re-ranker need about 950 MB and its free host has 512 MB, so it uses `EMBEDDINGS=openai` with Gemini, `VECTOR_STORE=pgvector` and no re-ranker, with the cut-offs measured again for that model. See [docs/DEPLOY.md](docs/DEPLOY.md).

More in [docs/DECISIONS.md](docs/DECISIONS.md).

---

## Docs

| Document | Description |
|---|---|
| [PRD](docs/PRD.md) | Product requirements: goals, user stories, non-goals |
| [Architecture](docs/ARCHITECTURE.md) | Ingestion, retrieval, answers, conflict check, API |
| [Decisions](docs/DECISIONS.md) | Every major technical decision and why, with the calibration numbers |
| [Setup](docs/SETUP.md) | Local dev setup and env vars |
| [Deploy](docs/DEPLOY.md) | Deployment notes |
| [Contributing](CONTRIBUTING.md) | How to propose changes |
| [Changelog](CHANGELOG.md) | What changed in each release |
| [Security](SECURITY.md) | How to report a vulnerability |

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>

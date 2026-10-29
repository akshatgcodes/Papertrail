# Setup

## Requirements

- Docker (for the Compose setup), or:
- Python 3.12 and [uv](https://docs.astral.sh/uv/), Node 20.19+ or 22.12+ (what Vite 8 needs)
- An API key for an OpenAI-compatible provider ([Groq](https://console.groq.com/keys) has a free tier), or Ollama running locally. Without one, the library, search and passages work, and questions stop after the passages are found.

## Everything with Docker

```bash
export GROQ_API_KEY=...
docker compose up --build
```

App: http://localhost:5173, password `papertrail` unless you set `APP_PASSWORD`. Set `WEB_PORT` to use another port.

Services: `db` (Postgres 17), `api` (FastAPI; the embedding and re-ranking models are built into the image), `web` (nginx serving the build and proxying `/api` with buffering off for the answer stream). The Chroma index and uploaded PDFs are in the `papertrail-data` volume.

## Without Docker

```bash
cd backend
uv sync
cp .env.example .env      # set APP_PASSWORD, SESSION_SECRET, LLM_API_KEY
uv run uvicorn main:app --reload        # http://localhost:8000/docs
```

```bash
cd frontend
npm install
npm run dev                              # http://localhost:5173, proxies /api to :8000
```

`VITE_API_PROXY` points the dev proxy somewhere else, e.g. `VITE_API_PROXY=http://localhost:8006 npm run dev`.

Locally the data goes to `backend/data/` (SQLite database, Chroma index, uploads). The first upload downloads the embedding model (`BAAI/bge-small-en-v1.5`) and the re-ranker (`Xenova/ms-marco-MiniLM-L-6-v2`), about 150 MB together.

## Environment

| Variable | Default | |
|---|---|---|
| `APP_PASSWORD` | (none) | required to log in |
| `SESSION_SECRET` | dev value | signs the session cookie; set a long random value |
| `FRONTEND_URL` | `http://localhost:5173` | allowed origin for CORS |
| `CROSS_SITE_COOKIES` | `false` | `true` when the frontend and API are on different sites |
| `DATABASE_URL` | SQLite in `DATA_DIR` | e.g. `postgresql+psycopg://user:pass@host:5432/papertrail` |
| `DATA_DIR` | `./data` | Chroma index and uploaded PDFs |
| `LLM_PROVIDER` | `groq` | `groq`, `openai` or `ollama` |
| `LLM_API_KEY` / `GROQ_API_KEY` | (none) | either works |
| `LLM_MODEL`, `LLM_BASE_URL` | per provider | `openai/gpt-oss-120b` on Groq, `gpt-4o-mini` on OpenAI, `llama3.2` on Ollama |
| `LLM_MAX_TOKENS` | `8000` | output budget; reasoning models spend part of it before answering |
| `EMBEDDING_MODEL`, `RERANKER_MODEL` | see above | any fastembed model; changing the embedding model means re-indexing and re-calibrating `MIN_SIMILARITY` |
| `RERANKER` | `fastembed` | `none` orders by word overlap instead |
| `MIN_SIMILARITY` | `0.68` | below this the library "doesn't cover" a question |
| `CANDIDATES`, `TOP_K`, `TOPIC_K`, `PER_DOC` | `30`, `8`, `14`, `3` | retrieval sizes |
| `CONFLICT_SIMILARITY`, `MAX_CONFLICT_PAIRS` | `0.75`, `4` | conflict check |
| `MAX_UPLOAD_MB`, `MAX_PAGES` | `20`, `500` | per file |

## Tests

```bash
cd backend && uv run pytest        # 52 tests, no network or model download
cd frontend && npm test
```

The backend tests use hashed bag-of-words embeddings, word-overlap ordering and a fake chat model. `TEST_DATABASE_URL` runs them on Postgres (CI does).

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>

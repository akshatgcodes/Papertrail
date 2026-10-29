# Deploy

Papertrail is **not deployed yet**. These are the intended setups.

## One server

`docker compose up -d --build` on a small VM with at least 2 GB of memory (the API container used about 750 MB after indexing four documents and answering a question locally), with TLS in front of the `web` service. In an `.env` next to the Compose file:

- `APP_PASSWORD`, `SESSION_SECRET` (long random values)
- `GROQ_API_KEY` or `LLM_API_KEY`
- `WEB_PORT` if 5173 isn't the port the proxy talks to

Back up both volumes: `pgdata` (documents, passages, history) and `papertrail-data` (the Chroma index and the original PDFs). The index can be rebuilt from the database with Re-index; the PDFs can't.

## Split hosting

| Part | Option |
|---|---|
| Frontend | Vercel (`frontend/`, build `npm run build`, output `dist`, SPA rewrite to `index.html`, `VITE_API_URL` set) |
| API | a container host with a **persistent disk** (Render with a disk, Fly.io with a volume, Railway with a volume), from `backend/Dockerfile`, `DATA_DIR` on the disk |
| Database | Neon Postgres |

API settings: `DATABASE_URL`, `FRONTEND_URL` and `CROSS_SITE_COOKIES=true`, plus the ones above.

Things to know:

- The Chroma index and PDFs live on the API's disk. A host without a persistent disk loses them on every deploy.
- Indexing runs inside the API process. Hosts that put idle instances to sleep can stop it halfway; the document then shows as failed with "Interrupted by a server restart", and Re-index finishes it.
- The proxy in front of the API must not buffer `text/event-stream` responses, or answers arrive all at once at the end. The API sends `X-Accel-Buffering: no` for nginx-style proxies.

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>

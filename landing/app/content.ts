import type { Site } from "./types";

export const site: Site = {
  name: "Papertrail",
  letter: "P",
  title: "Papertrail — ask your whole library, see where it disagrees",
  description:
    "A private knowledge base for your PDFs, notes and saved articles. Ask a question and get an answer drawn from all of them at once, with every passage cited, and a warning when two of your documents disagree.",
  meta: ["live", "PDFs · notes · web pages", "GPLv3"],
  headline: ["Ask your whole library.", "See where it disagrees."],
  intro:
    "A private knowledge base for your PDFs, notes and saved articles. Ask a question and get one answer drawn from all of them, with every passage cited, and a warning when two of your documents say things that can't both be true.",
  primary: { label: "Open Papertrail", href: "/app/" },
  repo: "https://github.com/akshatgcodes/Papertrail",
  note: "Demo password: `demo1234`. The demo runs on free hosting, so the first visit can take a minute to wake up.",
  xfactor: {
    title: "Many documents, one answer, and the disagreements.",
    intro:
      "Single-PDF chat is solved. Papertrail searches dozens of documents of different kinds together, and checks whether they contradict each other.",
    features: [
      {
        icon: "⌕",
        title: "Across everything",
        body: "30 candidate passages from the whole library, a cross-encoder re-ranks them, and at most three per document go to the model, so one long document can't crowd out the rest.",
      },
      {
        icon: "⚠",
        title: "Conflict cards",
        body: "Passages from different documents about the same thing are paired up and checked in one model call. \"Your notes say 2015; Wikipedia says 2020\" shows up with both sides.",
      },
      {
        icon: "¶",
        title: "Every claim cited",
        body: "Answers stream in with `[n]` citations. Click one to see the passage, then open it highlighted in its document, on the PDF page itself for PDFs.",
      },
    ],
  },
  preview: {
    intro:
      "An answer drawn from four documents with the passages behind it, a PDF page with the cited passage boxed, and the library with collections.",
    shots: [
      { src: "/shots/answer.png", alt: "An answer citing passages from four documents, with the sources listed beside it", caption: "Ask" },
      { src: "/shots/pdf.png", alt: "A PDF page with the cited passage highlighted", caption: "Cited passage, in place" },
      { src: "/shots/library.png", alt: "Library of documents grouped into collections", caption: "Library" },
    ],
  },
  stack: ["React 19", "TypeScript", "Vite", "FastAPI", "SSE", "SQLAlchemy", "PostgreSQL", "pgvector", "Chroma", "LangChain", "fastembed", "Groq", "PyMuPDF", "pytest", "Vitest"],
  concepts: [
    { title: "Calibrated cut-off", body: "With the local embedding model, on a 55-document test library, covered questions scored 0.766–0.859 and uncovered ones 0.466–0.621. Below the cut-off in that gap, the model isn't called at all." },
    { title: "Cheap conflict check", body: "Pairs are pre-filtered without a model: different documents, similar enough, at least one side cited, one pair per two documents. Then one JSON call." },
    { title: "Topic mode", body: "\"What do I know about attention?\" isn't a question, so it pulls more passages and writes a grouped summary of what your documents say." },
    { title: "Add anything", body: "PDFs, Markdown and text files, web pages by URL, or notes written in the app. Indexing runs in the background." },
    { title: "Two storage setups", body: "Locally: Chroma on disk and local ONNX embeddings, no key needed. On a small host (like this demo): pgvector in Postgres, an embeddings API and no re-ranker." },
    { title: "History with permalinks", body: "Every question is saved with its answer, sources and conflicts." },
  ],
  run: {
    title: "Run your own",
    intro: "Docker Compose runs Postgres, the API and the app. Embeddings and re-ranking run locally, so only the answer model needs a key.",
    blocks: [
      {
        title: "Docker",
        steps: [
          { text: "Clone and start it with a Groq key (free tier):", cmd: "git clone https://github.com/akshatgcodes/Papertrail\ncd Papertrail\nGROQ_API_KEY=... docker compose up --build" },
          { text: "Open it (password `papertrail`):", cmd: "http://localhost:5173" },
        ],
      },
    ],
  },
  tagline: "a knowledge base that shows where your documents disagree.",
};

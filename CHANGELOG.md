# Changelog

All notable changes to **Papertrail** are documented here.

---

## [Unreleased]

---

## [0.1.0] — 2026-10-30

### ✨ Added
- Library of PDFs, Markdown and text files, web pages by URL, and notes, sorted into collections; indexing in the background with status and failure reasons
- Passages along headings with exact offsets (text) or page and block positions (PDF); web pages reduced to their content, with references and navigation dropped
- Local embeddings (bge-small) in Chroma and a local cross-encoder re-ranker; scope by collection or chosen documents
- Retrieval with a calibrated similarity cut-off (no model call when the library doesn't cover a question) and a per-document cap
- Streamed answers with numbered citations, and a topic mode that summarises what the library says
- Conflict check between cited documents: similar cross-document passage pairs compared in one model call
- Document view with the cited passage highlighted, on the rendered page for PDFs; editable notes
- History with permalinks; Docker Compose with Postgres and nginx

### 🧪 Tests
- Passage splitting, web extraction and URL checks, every document route, retrieval scope and the per-document cap, the answer stream end to end with a fake model, conflict pairing and parsing; on SQLite and Postgres
- Answer rendering, source grouping and the stream reducer

---

[Unreleased]: https://github.com/akshatgcodes/Papertrail/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/akshatgcodes/Papertrail/releases/tag/v0.1.0

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>

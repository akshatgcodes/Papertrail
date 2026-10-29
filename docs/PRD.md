# PRD: Papertrail

## Problem

What you know is spread over PDFs in a downloads folder, notes in a notes app, and articles saved in browser tabs. Search finds a word, not an answer. A chatbot over one PDF helps with that PDF, but the useful questions cut across documents: "what did I read about X", "which of these says Y". And when two sources disagree, nobody tells you; you only notice if you happen to read both.

## Goal

A private knowledge base that takes PDFs, Markdown and text files, web pages and notes, and answers questions across all of them at once. Every claim in an answer points to the exact passage it came from. When documents disagree about the same thing, the answer says so and shows both sides. A topic mode summarises everything the library says about a subject.

## Users

- A student or engineer with a reading pile: papers, docs pages, lecture notes, their own notes
- Someone checking their own notes against the sources they were written from

## User stories

| As a… | I want to… | So that… |
|---|---|---|
| reader | drop in PDFs, Markdown files, links and notes | everything I've read is in one place |
| reader | sort documents into collections | I can ask within one subject |
| reader | ask a question and get an answer from all my documents | I don't have to know which document has it |
| reader | see the exact passage behind each part of the answer | I can check it |
| reader | open that passage highlighted in its document or on its PDF page | I can read the context around it |
| reader | be told when my documents disagree, with both claims | I don't trust a wrong note |
| reader | ask "what do I know about X" | I get a summary instead of a single answer |
| reader | be told plainly when the library doesn't cover something | I'm not given an answer from the model's own memory |
| reader | see my past questions with their answers | I can come back to them |

## Requirements

- Upload PDF, `.md`, `.markdown`, `.txt` (several at once, up to 20 MB and 500 pages each); import a URL; write notes
- Indexing in the background: parse, split into passages, embed, store; documents show processing, ready or failed (with the reason)
- Retrieval across the whole library, one collection, or chosen documents; re-ranked; several documents represented
- No model call when nothing in the library is close to the question
- Streamed answers with numbered citations; the passages shown beside the answer, grouped by document
- Conflict check between cited documents after the answer
- Topic mode with a structured summary
- Saved history with permalinks
- One owner, password login; works with any OpenAI-compatible model

## Non-goals

- Several users or sharing; it's one person's library
- OCR for scanned PDFs (they fail with a clear reason)
- Office formats (Word, PowerPoint), images, audio
- Crawling: a URL imports that one page
- Chat with follow-up questions; each question stands alone, which keeps the citations unambiguous

## Success measures

- Questions the library covers are answered with citations; off-topic questions stop before the model (checked against a 55-document test library, see [DECISIONS.md](DECISIONS.md))
- A planted contradiction between a note and a reference page is reported as a conflict
- A question about a topic covered by several documents cites more than one of them

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>

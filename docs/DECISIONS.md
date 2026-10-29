# Decisions

## Embeddings run locally (fastembed), not through an API

The plan said OpenAI embeddings. A library's vectors are tied to the model that made them: switch models and every passage has to be embedded again, and every similarity threshold has to be measured again. So the embedding model should be one that doesn't change or disappear under you. `BAAI/bge-small-en-v1.5` through fastembed runs on the CPU (ONNX), needs no key, costs nothing per document, and gives identical scores on every run, which is what made the cut-off below measurable. The answer model is still any OpenAI-compatible API, Groq by default (OpenAI's `gpt-4o-mini` and Ollama are one setting away).

## One Chroma collection, scoped by metadata

"Namespacing" could mean one Chroma collection per document collection. That makes "search everything" a fan-out over collections with scores merged afterwards, and moving a document between collections a re-embed. Instead there's one collection of passages, each tagged with `document_id` and `collection`, and a scope is a `where` filter. Moving a document rewrites its metadata only.

## Passages follow headings and keep their position

Splitting by a fixed character count cuts sections in half and loses what a passage is about. Markdown, notes and imported web pages are split along headings first, and each passage carries its heading path ("Python › Releases"), which is embedded with it and shown in the sources. Passages also keep their character offsets (or, for PDFs, page and block rectangles), so the document view can highlight exactly what was cited instead of searching for the text again.

Overlap only applies where a paragraph is longer than a passage (1,000 characters): it's split at sentence ends and each piece starts with the previous one's last sentence. Between paragraphs the heading structure already gives the context, and overlap would just repeat text in the excerpts.

## Web pages: drop by class token, not substring

The first version dropped every element whose class *contained* "toc", "nav", "ads" and so on. Wikipedia's `<body class="vector-toc-available">` matched, and every Wikipedia page came out empty; React's docs did too. Now each class name is matched whole against the pattern (`navbox`, `mw-editsection`, `reflist`), `html`, `body`, `main` and `article` are never dropped, and sections titled References, External links, See also and similar are skipped.

## The "not in your library" cut-off

Before any model call, the best passage's cosine similarity to the question decides whether the library covers it at all. Measured on a test library of 55 documents (48 Wikipedia articles, 3 docs pages, 3 notes, 1 paper; 1,935 passages):

| Questions the library covers | Best similarity |
|---|---|
| When did Python 2 reach end of life? | 0.837 |
| Who created Python? | 0.794 |
| What does useEffect's cleanup function do? | 0.841 |
| How many encoder layers does the base Transformer have? | 0.830 |
| What is QUIC? | 0.799 |
| How does Redis persist data? | 0.811 |
| What is the difference between HTTP/2 and HTTP/3? | 0.834 |
| What is retrieval-augmented generation? | 0.859 |
| When should I use a FastAPI background task? | 0.833 |
| What is a Kubernetes pod? | 0.828 |
| How does gradient descent work? | 0.855 |
| What license is SQLite released under? | 0.766 |

| Questions it doesn't | Best similarity |
|---|---|
| How do I bake sourdough bread? | 0.495 |
| Who won the 2018 FIFA World Cup? | 0.500 |
| What is the capital of Australia? | 0.466 |
| How does photosynthesis work? | 0.592 |
| What is the price of Bitcoin? | 0.595 |
| How do vaccines train the immune system? | 0.621 |
| What is the best marathon training plan? | 0.571 |
| Who painted the Mona Lisa? | 0.506 |

The lowest covered question is 0.766 and the highest uncovered one is 0.621. The cut-off is 0.68, a little below the middle of the gap, because answering an uncovered question costs one model call that ends in "not in library", while refusing a covered one loses the answer. The numbers belong to bge-small; another embedding model needs this measured again.

Retrieval for these questions took about 300 to 900 ms on a laptop CPU, including re-ranking 30 candidates.

## Re-rank, then cap per document

Vector search compares the question and a passage as two separate vectors. The cross-encoder (`ms-marco-MiniLM-L-6-v2`) reads them together, which is better at telling "uses the same words" from "answers it", and slow enough that it only sees the 30 candidates.

Then passages are taken in re-ranked order with at most 3 per document. Without the cap, one long article (the test library has a 105-passage one) can fill all 8 slots for a question several documents answer, and a disagreement between documents can't be seen if only one document is in the excerpts. With it, the questions above drew on 1 to 5 documents each, depending on how many cover the subject.

## Conflict detection in two steps

Comparing every pair of 8 passages with a model is 28 comparisons per question. Most pairs are about different things and can't contradict each other usefully. So:

1. **No model:** pairs of passages from different documents whose embeddings are at least 0.75 similar, where at least one passage was cited in the answer; the most similar pair per two documents; no passage in more than two pairs; at most 4 pairs.
2. **One model call** for all of them, answering in JSON per pair: conflict or not, the topic, each side's claim, and why both can't be right. The prompt lists what is *not* a conflict (more detail, a different aspect, different wording, a claim the passages themselves place at a different time), because without that a model tends to report any two different-looking passages.

The pairing rules come from a failure. The first version took the four most similar cross-document pairs, full stop. For "When did Python 2 reach end of life?", all four went to two Wikipedia articles about Python (similarity 0.90 to 0.95) that agree with each other, and the note claiming 2015 was never compared. One pair per two documents, and requiring a cited passage, put the note next to the Wikipedia passage on the end-of-life date.

Planted conflicts in the test library and how similar their passages are: Python 2 end of life, note against Wikipedia, 0.839; `useEffect` timing, note against React docs, 0.889; HTTP/2 connections, note against Wikipedia, 0.831; a PostgreSQL fact, note against Wikipedia, 0.813. All clear the 0.75 bar.

## SSE over POST, and saving in `finally`

The question and its scope go in a JSON body, so the stream is a `POST` read with `fetch` and a small parser; `EventSource` can only `GET`. The query is written to history in a `finally` block, so an answer the browser abandons is still saved, marked stopped. An early version returned from inside that `try` for "not found" and "declined", which skipped the final `done` event; the steps now run in an inner generator, and the tests check every path ends with `done`.

## Provider errors stay in the log

Groq's rate-limit error includes the organisation id. The page gets a short message (rate limit, rejected key, timeout, or the error's type); the full text goes to the server log.

## Indexing in a FastAPI background task, not a queue

Indexing a document takes seconds, happens a few times a day, and needs no retries beyond "Re-index". A worker and a broker would be a second process to deploy for that. Indexing runs after the upload response, one document at a time behind a lock (the ONNX model already uses every core). The cost: a restart interrupts it, so startup marks anything still "processing" as failed with that reason.

## What I'd do differently in v2

- Hybrid search: add BM25 next to the vectors, so exact names, numbers and error codes are found even when the embedding misses them.
- OCR for scanned PDFs.
- Re-check conflicts across the whole library on a schedule, not only between the passages of one answer.

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>

"""Do two documents disagree about the same thing?

Step 1, no model: among the chosen passages, pair up ones from *different* documents
whose embeddings are close (cosine >= CONFLICT_SIMILARITY). Close passages are about the
same subject; far ones can't contradict each other in a useful way.

Step 2, one model call: show the pairs and ask, per pair, whether they make claims about
the same specific thing that can't both be true. Different aspects, more detail, or
different wording are not conflicts.
"""

import json
import logging
import math
from dataclasses import dataclass

from app import answer, store
from app.config import settings
from app.retrieval import Source

log = logging.getLogger("papertrail.conflicts")

SYSTEM = """You check whether two passages from different documents contradict each other.

A conflict means both passages make a claim about the same specific thing, and the claims
can't both be true: different numbers, dates, versions, names, yes/no answers or
recommendations. These are NOT conflicts: one passage having more detail, the two covering
different aspects of a topic, different wording for the same claim, or a claim that was
true at a different time when the passages say so.

Answer with JSON only:
{"results": [{"pair": 1, "conflict": true, "topic": "a few words",
"claim_a": "what passage A says, short", "claim_b": "what passage B says, short",
"note": "one sentence on why they can't both be right"}]}
Include every pair. For pairs without a conflict, set "conflict": false and leave the
other fields empty."""


@dataclass
class Pair:
    a: Source
    b: Source
    similarity: float


def cosine(u: list[float], v: list[float]) -> float:
    dot = sum(x * y for x, y in zip(u, v, strict=True))
    nu, nv = math.sqrt(sum(x * x for x in u)), math.sqrt(sum(y * y for y in v))
    return dot / (nu * nv) if nu and nv else 0.0


def candidate_pairs(
    sources: list[Source], vecs: dict[int, list[float]], cited: set[int] | None = None
) -> list[Pair]:
    pairs = []
    for i, a in enumerate(sources):
        for b in sources[i + 1 :]:
            if a.document_id == b.document_id or a.chunk_id not in vecs or b.chunk_id not in vecs:
                continue
            if cited and a.n not in cited and b.n not in cited:
                continue
            sim = cosine(vecs[a.chunk_id], vecs[b.chunk_id])
            if sim >= settings.conflict_similarity:
                pairs.append(Pair(a, b, round(sim, 4)))
    pairs.sort(key=lambda p: -p.similarity)
    # Spread the budget: one pair per two documents, and no passage in more than two.
    # Otherwise two near-identical articles (which rarely disagree) take every slot
    seen_docs: set[tuple[int, int]] = set()
    used: dict[int, int] = {}
    out = []
    for p in pairs:
        docs = tuple(sorted((p.a.document_id, p.b.document_id)))
        if docs in seen_docs or used.get(p.a.chunk_id, 0) >= 2 or used.get(p.b.chunk_id, 0) >= 2:
            continue
        seen_docs.add(docs)
        used[p.a.chunk_id] = used.get(p.a.chunk_id, 0) + 1
        used[p.b.chunk_id] = used.get(p.b.chunk_id, 0) + 1
        out.append(p)
        if len(out) == settings.max_conflict_pairs:
            break
    return out


def find_pairs(sources: list[Source], cited: set[int] | None = None) -> list[Pair]:
    """Each pair has at least one passage the answer cited (any, if it cited none): a
    disagreement matters when it touches what the answer relied on."""
    return candidate_pairs(sources, store.vectors([s.chunk_id for s in sources]), cited)


def _prompt(pairs: list[Pair]) -> str:
    parts = []
    for i, p in enumerate(pairs, 1):
        parts.append(
            f"Pair {i}\nA ({answer.excerpt(p.a).split(chr(10), 1)[0]}):\n{p.a.text}\n\n"
            f"B ({answer.excerpt(p.b).split(chr(10), 1)[0]}):\n{p.b.text}"
        )
    return "\n\n---\n\n".join(parts)


def parse(raw: str, pairs: list[Pair]) -> list[dict]:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1:
        raise ValueError("no JSON in reply")
    data = json.loads(raw[start : end + 1])
    out = []
    for item in data.get("results", []):
        try:
            i = int(item.get("pair"))
        except (TypeError, ValueError):
            continue
        if not item.get("conflict") or not 1 <= i <= len(pairs):
            continue
        p = pairs[i - 1]
        out.append(
            {
                "topic": str(item.get("topic") or "").strip()[:200],
                "claim_a": str(item.get("claim_a") or "").strip()[:500],
                "claim_b": str(item.get("claim_b") or "").strip()[:500],
                "note": str(item.get("note") or "").strip()[:500],
                "a": p.a.n,
                "b": p.b.n,
                "similarity": p.similarity,
            }
        )
    return out


def check(pairs: list[Pair], model=None) -> list[dict]:
    """Conflicts among `pairs`, as dicts pointing at source numbers. Raises
    GenerationError if the model can't be reached or answers nonsense."""
    if not pairs:
        return []
    try:
        model = model or answer.chat_model()
        reply = model.invoke([("system", SYSTEM), ("human", _prompt(pairs))])
        raw = reply.content if isinstance(reply.content, str) else str(reply.content)
        return parse(raw, pairs)
    except answer.GenerationError:
        raise
    except Exception as e:
        log.warning("conflict check failed: %s", e)
        raise answer.GenerationError(f"Conflict check failed: {type(e).__name__}") from e

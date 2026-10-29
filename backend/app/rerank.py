"""Second-stage ordering. Vector search compares a question and a passage as two separate
embeddings; a cross-encoder reads them together, which is slower but better at telling
"mentions the same words" from "answers the question". It runs on the 30 candidates
only, locally (ONNX, no key)."""

import re
from functools import lru_cache

from app.config import settings


class Reranker:
    def score(self, query: str, texts: list[str]) -> list[float]:
        raise NotImplementedError


class CrossEncoder(Reranker):
    def __init__(self, model: str):
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self.model = TextCrossEncoder(model)

    def score(self, query: str, texts: list[str]) -> list[float]:
        return [float(s) for s in self.model.rerank(query, texts)] if texts else []


class WordOverlap(Reranker):
    """Share of the query's words found in the passage. For tests and RERANKER=none."""

    def score(self, query: str, texts: list[str]) -> list[float]:
        words = set(re.findall(r"[a-z0-9]{3,}", query.lower()))
        return [
            len(words & set(re.findall(r"[a-z0-9]{3,}", t.lower()))) / (len(words) or 1)
            for t in texts
        ]


@lru_cache
def get_reranker() -> Reranker:
    if settings.reranker == "fastembed":
        return CrossEncoder(settings.reranker_model)
    return WordOverlap()

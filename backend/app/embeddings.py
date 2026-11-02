import hashlib
import math
import re
import time
from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.config import settings


class FastEmbedEmbeddings(Embeddings):
    """Local ONNX embeddings: no API key, no GPU, same scores every run."""

    def __init__(self, model: str):
        from fastembed import TextEmbedding

        self.model = TextEmbedding(model)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self.model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self.model.query_embed(text))).tolist()


class HashEmbeddings(Embeddings):
    """Bag-of-words hashed into a fixed vector. Crude, but deterministic and
    dependency-free, and shared words still mean higher cosine similarity, which is
    all the tests need."""

    DIM = 256

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.DIM
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            v[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.DIM] += 1
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


class PacedEmbeddings(Embeddings):
    """Free API tiers cap inputs per minute (Gemini: 100), and a long PDF has more passages
    than that. Send them in batches and, when the provider says slow down, wait and carry on
    instead of failing the whole document."""

    def __init__(
        self, inner: Embeddings, batch: int = 100, max_wait: float = 600.0, sleep=time.sleep
    ):
        self.inner, self.batch, self.max_wait, self.sleep = inner, batch, max_wait, sleep

    def _call(self, fn, arg):
        waited = 0.0
        while True:
            try:
                return fn(arg)
            except Exception as e:
                if not _rate_limited(e) or waited >= self.max_wait:
                    raise
                delay = _retry_after(e)
                self.sleep(delay)
                waited += delay

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            out += self._call(self.inner.embed_documents, texts[i : i + self.batch])
        return out

    def embed_query(self, text: str) -> list[float]:
        return self._call(self.inner.embed_query, text)


def _rate_limited(e: Exception) -> bool:
    return getattr(e, "status_code", None) == 429 or type(e).__name__ == "RateLimitError"


def _retry_after(e: Exception) -> float:
    """Seconds to wait: the Retry-After header when there is one, else 20, never over 60."""
    headers = getattr(getattr(e, "response", None), "headers", None) or {}
    try:
        return min(max(float(headers.get("retry-after", 20)), 1.0), 60.0)
    except (TypeError, ValueError):
        return 20.0


def api_embeddings() -> Embeddings:
    """Any OpenAI-compatible embeddings endpoint (Gemini, OpenAI, Ollama). For small hosts:
    the local model needs more memory than a 512 MB instance has."""
    from langchain_openai import OpenAIEmbeddings

    return PacedEmbeddings(
        OpenAIEmbeddings(
            model=settings.embedding_model,
            base_url=settings.embeddings_base_url or None,
            api_key=settings.embeddings_api_key,
            dimensions=settings.embedding_dimensions or None,
            # Send plain text: the default tokenises with tiktoken, which only OpenAI accepts
            check_embedding_ctx_length=False,
            chunk_size=100,
            max_retries=1,  # PacedEmbeddings does the waiting
            timeout=60,  # a dropped connection would otherwise hang the upload forever
        )
    )


@lru_cache
def get_embeddings() -> Embeddings:
    if settings.embeddings == "hash":
        return HashEmbeddings()
    if settings.embeddings == "openai":
        return api_embeddings()
    return FastEmbedEmbeddings(settings.embedding_model)

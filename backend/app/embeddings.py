import hashlib
import math
import re
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


def api_embeddings() -> Embeddings:
    """Any OpenAI-compatible embeddings endpoint (Gemini, OpenAI, Ollama). For small hosts:
    the local model needs more memory than a 512 MB instance has."""
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.embedding_model,
        base_url=settings.embeddings_base_url or None,
        api_key=settings.embeddings_api_key,
        dimensions=settings.embedding_dimensions or None,
        # Send plain text: the default tokenises with tiktoken, which only OpenAI accepts
        check_embedding_ctx_length=False,
        chunk_size=100,
    )


@lru_cache
def get_embeddings() -> Embeddings:
    if settings.embeddings == "hash":
        return HashEmbeddings()
    if settings.embeddings == "openai":
        return api_embeddings()
    return FastEmbedEmbeddings(settings.embedding_model)

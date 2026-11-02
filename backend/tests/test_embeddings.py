import pytest

from app.embeddings import PacedEmbeddings


class Limited(Exception):
    status_code = 429


class Fake:
    """Answers with the text length, after failing `fails` times with a 429."""

    def __init__(self, fails: int = 0):
        self.fails, self.calls = fails, []

    def embed_documents(self, texts):
        self.calls.append(len(texts))
        if self.fails:
            self.fails -= 1
            raise Limited()
        return [[float(len(t))] for t in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


def test_batches_and_keeps_order():
    fake = Fake()
    out = PacedEmbeddings(fake, batch=2, sleep=lambda s: None).embed_documents(
        ["a", "bb", "ccc", "dddd", "e"]
    )
    assert out == [[1.0], [2.0], [3.0], [4.0], [1.0]]
    assert fake.calls == [2, 2, 1]


def test_waits_and_resumes_after_rate_limit():
    slept = []
    fake = Fake(fails=2)
    out = PacedEmbeddings(fake, batch=10, sleep=slept.append).embed_documents(["a", "bb"])
    assert out == [[1.0], [2.0]]
    assert slept == [20.0, 20.0]
    assert PacedEmbeddings(Fake(fails=1), sleep=slept.append).embed_query("abc") == [3.0]


def test_gives_up_after_max_wait_and_passes_other_errors():
    with pytest.raises(Limited):
        PacedEmbeddings(Fake(fails=100), max_wait=50, sleep=lambda s: None).embed_documents(["a"])

    class Broken:
        def embed_documents(self, texts):
            raise ValueError("bad input")

    with pytest.raises(ValueError):
        PacedEmbeddings(Broken(), sleep=lambda s: None).embed_documents(["a"])

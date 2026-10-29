"""Prompts and the streaming call for both modes.

ask:   a question, answered from the excerpts, with [n] citations
topic: "what do I know about X": a synthesis of everything the excerpts say about X

Either way the model may reply NOT_IN_LIBRARY when the excerpts don't cover it, and it is
told to point out disagreements between documents instead of quietly picking one.
"""

import logging
import re
from collections.abc import Iterator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.retrieval import Source

log = logging.getLogger("papertrail.answer")

DECLINE = "NOT_IN_LIBRARY"

COMMON = f"""Rules:
- Use only the excerpts. No outside knowledge, even if you know the answer.
- Cite the excerpts that support each sentence or bullet, like [1] or [2][4].
- If excerpts from different documents disagree, say so plainly and cite both sides.
  Don't silently pick one.
- If the excerpts answer only part of it, answer that part and say what they don't cover.
- Reply with exactly {DECLINE} and nothing else only when no excerpt bears on it at all."""

ASK_SYSTEM = f"""You answer questions from the user's personal library: their PDFs, notes,
saved articles. You get numbered excerpts, each labelled with its document.

{COMMON}
- Be concise: a few sentences, or a short list when the question asks for several items."""

TOPIC_SYSTEM = f"""The user wants to know what their personal library (PDFs, notes, saved
articles) says about a topic. You get numbered excerpts, each labelled with its document.

Write a synthesis of what the excerpts say about the topic:
- Start with a two-sentence overview.
- Then group related points under short `###` headings, as bullet points.
- Mention which documents cover the topic, and anything they disagree on.

{COMMON}"""


class GenerationError(Exception):
    pass


def describe(e: Exception) -> str:
    """A message for the page. Provider errors can carry account details (Groq's 429
    names the organisation), so the full text only goes to the log."""
    log.warning("model call failed: %s", e)
    name = type(e).__name__
    if "RateLimit" in name or getattr(e, "status_code", None) == 429:
        return "The model provider's rate limit was reached. Try again in a few minutes."
    if "Authentication" in name or getattr(e, "status_code", None) == 401:
        return "The model provider rejected the API key."
    if "Timeout" in name:
        return "The model took too long to answer."
    return f"The language model call failed ({name})."


def chat_model() -> BaseChatModel:
    """Tests replace this with a fake model."""
    from langchain_openai import ChatOpenAI

    base_url, model, key = settings.llm
    if not key:
        raise GenerationError("No LLM API key. Set LLM_API_KEY (or GROQ_API_KEY) in backend/.env")
    return ChatOpenAI(
        base_url=base_url,
        model=model,
        api_key=key,
        temperature=0,
        timeout=90,
        max_tokens=settings.llm_max_tokens,
    )


def citations(answer: str) -> set[int]:
    return {
        int(n)
        for group in re.findall(r"\[(\d+(?:\s*[,\]\[]\s*\d+)*)\]", answer)
        for n in re.findall(r"\d+", group)
    }


def normalize_citations(answer: str) -> str:
    """gpt-oss on Groq sometimes cites as 【1】 or 【1†source】 despite the prompt."""
    return re.sub(r"【\s*(\d+)(?:\s*†[^】]*)?】", r"[\1]", answer)


def excerpt(s: Source) -> str:
    where = s.title + (f" › {s.heading}" if s.heading else "")
    if s.page is not None:
        where += f" (page {s.page + 1})"
    return f"[{s.n}] {where}\n{s.text}"


def build_prompt(mode: str, query: str, sources: list[Source]) -> list:
    excerpts = "\n\n".join(excerpt(s) for s in sources)
    if mode == "topic":
        return [
            SystemMessage(TOPIC_SYSTEM),
            HumanMessage(f"Excerpts:\n\n{excerpts}\n\nTopic: {query}"),
        ]
    return [
        SystemMessage(ASK_SYSTEM),
        HumanMessage(f"Excerpts:\n\n{excerpts}\n\nQuestion: {query}"),
    ]


def stream(mode: str, query: str, sources: list[Source], model=None) -> Iterator[str]:
    """Yields text deltas. Raises GenerationError if the call fails."""
    try:
        model = model or chat_model()
        for chunk in model.stream(build_prompt(mode, query, sources)):
            text = chunk.content if isinstance(chunk.content, str) else ""
            if text:
                yield text
    except GenerationError:
        raise
    except Exception as e:
        raise GenerationError(describe(e)) from e

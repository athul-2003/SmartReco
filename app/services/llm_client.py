import logging
import time
from collections.abc import Iterator
from functools import lru_cache

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

MESH_BASE_URL = "https://api.meshapi.ai/v1"
EMBED_MODEL = "sentence-transformers/all-minilm-l6-v2"
CHAT_MODEL = "openai/chat-latest"
CHAT_MAX_RETRIES = 3
CHAT_BACKOFF_BASE_SECONDS = 2


class LLMClient:
    """Thin wrapper around the openai SDK pointed at Mesh. Every AI call in
    SmartReco goes through this class - callers never touch the SDK directly,
    keeping Mesh usage centralized and easy to audit."""

    def __init__(self, api_key: str):
        self._client = OpenAI(base_url=MESH_BASE_URL, api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=EMBED_MODEL, input=texts)
        return [item.embedding for item in response.data]

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Non-streaming chat completion, with light retry/backoff on
        transient failures - mirrors embeddings.py's embed retry. Unlike
        embed() (already retried once by embeddings.py's own wrapper, so
        retrying again here would double it), nothing else protects this
        call - chat_stream() deliberately has no retry of its own, since a
        caller streaming partial tokens can't transparently retry mid-stream
        (see recommendations.py's /stream route, which instead catches and
        keeps whatever text already arrived)."""
        last_error: Exception | None = None
        for attempt in range(CHAT_MAX_RETRIES):
            try:
                response = self._client.chat.completions.create(
                    model=CHAT_MODEL, messages=messages
                )
                return response.choices[0].message.content or ""
            except Exception as exc:  # noqa: BLE001 - retry on any Mesh/network failure
                last_error = exc
                wait = CHAT_BACKOFF_BASE_SECONDS * (2**attempt)
                logger.warning(
                    "Chat completion failed (attempt %d/%d): %s - retrying in %ds",
                    attempt + 1,
                    CHAT_MAX_RETRIES,
                    exc,
                    wait,
                )
                time.sleep(wait)
        raise last_error

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """Yields narrative text as it's generated, instead of waiting for
        the full completion - lets a slow generation feel responsive."""
        stream = self._client.chat.completions.create(
            model=CHAT_MODEL, messages=messages, stream=True
        )
        for chunk in stream:
            # Some chunks carry no choices at all (e.g. a trailing
            # usage/metadata chunk) - not every streamed chunk represents a
            # token delta.
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


@lru_cache
def get_llm_client() -> LLMClient:
    settings = get_settings()
    return LLMClient(api_key=settings.mesh_api_key)

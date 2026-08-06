from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.llm_client import CHAT_MAX_RETRIES, LLMClient


def _chunk(content: str | None = None, has_choices: bool = True):
    if not has_choices:
        # Some providers (Mesh included) send chunks with an empty choices
        # list - e.g. a trailing usage/metadata chunk - not every streamed
        # chunk represents a token delta.
        return SimpleNamespace(choices=[])
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content))]
    )


def test_chat_stream_skips_chunks_with_no_choices():
    # Regression test: an unguarded chunk.choices[0] crashed the entire
    # stream with an IndexError the moment Mesh sent an empty-choices
    # chunk, killing the SSE response mid-generation.
    client = LLMClient(api_key="test-key")
    client._client = MagicMock()
    client._client.chat.completions.create.return_value = [
        _chunk(has_choices=False),
        _chunk(content="Hello "),
        _chunk(content=None),  # choices present, but no text delta (e.g. role-only)
        _chunk(content="world"),
        _chunk(has_choices=False),
    ]

    result = list(client.chat_stream([{"role": "user", "content": "hi"}]))
    assert result == ["Hello ", "world"]


def _chat_completion(content: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_chat_retries_on_transient_failure_then_succeeds(monkeypatch):
    monkeypatch.setattr("app.services.llm_client.time.sleep", lambda seconds: None)
    client = LLMClient(api_key="test-key")
    client._client = MagicMock()
    client._client.chat.completions.create.side_effect = [
        RuntimeError("Mesh had a bad day"),
        _chat_completion("Great fit for you."),
    ]

    result = client.chat([{"role": "user", "content": "hi"}])

    assert result == "Great fit for you."
    assert client._client.chat.completions.create.call_count == 2


def test_chat_raises_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr("app.services.llm_client.time.sleep", lambda seconds: None)
    client = LLMClient(api_key="test-key")
    client._client = MagicMock()
    client._client.chat.completions.create.side_effect = RuntimeError("Mesh is down")

    with pytest.raises(RuntimeError, match="Mesh is down"):
        client.chat([{"role": "user", "content": "hi"}])

    assert client._client.chat.completions.create.call_count == CHAT_MAX_RETRIES

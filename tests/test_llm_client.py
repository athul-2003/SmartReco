from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.llm_client import LLMClient


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

from functools import lru_cache

from openai import OpenAI

from app.config import get_settings

MESH_BASE_URL = "https://api.meshapi.ai/v1"
EMBED_MODEL = "sentence-transformers/all-minilm-l6-v2"
CHAT_MODEL = "openai/chat-latest"


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
        response = self._client.chat.completions.create(
            model=CHAT_MODEL, messages=messages
        )
        return response.choices[0].message.content or ""


@lru_cache
def get_llm_client() -> LLMClient:
    settings = get_settings()
    return LLMClient(api_key=settings.mesh_api_key)

import logging
import time

from app.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 2


def build_embedding_text(title: str, description: str) -> str:
    return f"{title}. {description}".strip()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts via Mesh in batches of BATCH_SIZE, with light retry/backoff
    on transient failures (e.g. rate limits) - see SRS Sec. 9.2."""
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        embeddings.extend(_embed_batch_with_retry(batch))
    return embeddings


def _embed_batch_with_retry(batch: list[str]) -> list[list[float]]:
    client = get_llm_client()
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return client.embed(batch)
        except Exception as exc:  # noqa: BLE001 - retry on any Mesh/network failure, not just specific SDK errors
            last_error = exc
            wait = BACKOFF_BASE_SECONDS * (2**attempt)
            logger.warning(
                "Embedding batch failed (attempt %d/%d): %s - retrying in %ds",
                attempt + 1,
                MAX_RETRIES,
                exc,
                wait,
            )
            time.sleep(wait)
    raise last_error

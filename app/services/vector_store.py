from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import get_settings

COLLECTION_NAME = "products"
VECTOR_SIZE = 384  # sentence-transformers/all-minilm-l6-v2


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection() -> None:
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


def upsert_product(
    product_id: int, vector: list[float], title: str, category: str, price: float
) -> None:
    ensure_collection()
    client = get_qdrant_client()
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            {
                "id": product_id,
                "vector": vector,
                "payload": {"title": title, "category": category, "price": price},
            }
        ],
    )


def delete_product(product_id: int) -> None:
    ensure_collection()
    client = get_qdrant_client()
    client.delete(collection_name=COLLECTION_NAME, points_selector=[product_id])


def get_indexed_ids() -> set[int]:
    """All product IDs currently stored in Qdrant - lets the seed script skip
    products it has already embedded (resumable seeding, SRS Sec. 9.2)."""
    ensure_collection()
    client = get_qdrant_client()
    ids: set[int] = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        ids.update(p.id for p in points)
        if offset is None:
            break
    return ids


def count() -> int:
    ensure_collection()
    client = get_qdrant_client()
    return client.count(collection_name=COLLECTION_NAME).count


def search(vector: list[float], top_k: int = 5) -> list[dict]:
    """Top-K semantic search (FR-4.2) - returns real catalog product IDs plus
    their payload and similarity score, never invented data."""
    ensure_collection()
    client = get_qdrant_client()
    results = client.query_points(
        collection_name=COLLECTION_NAME, query=vector, limit=top_k
    )
    return [
        {"id": point.id, "score": point.score, **point.payload}
        for point in results.points
    ]

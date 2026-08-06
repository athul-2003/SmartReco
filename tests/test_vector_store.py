from types import SimpleNamespace
from unittest.mock import MagicMock

from qdrant_client.models import FieldCondition, MatchValue, Range

from app.services import vector_store


def test_build_filter_returns_none_when_unfiltered():
    assert vector_store._build_filter(None, None) is None


def test_build_filter_category_only():
    result = vector_store._build_filter("Dev", None)
    assert result.must == [
        FieldCondition(key="category", match=MatchValue(value="Dev"))
    ]


def test_build_filter_max_price_only():
    result = vector_store._build_filter(None, 500)
    assert result.must == [FieldCondition(key="price", range=Range(lte=500))]


def test_build_filter_both():
    result = vector_store._build_filter("Dev", 500)
    assert result.must == [
        FieldCondition(key="category", match=MatchValue(value="Dev")),
        FieldCondition(key="price", range=Range(lte=500)),
    ]


def test_search_passes_filter_through_to_qdrant(monkeypatch):
    fake_client = MagicMock()
    fake_client.collection_exists.return_value = True
    fake_client.query_points.return_value = SimpleNamespace(points=[])
    monkeypatch.setattr(vector_store, "get_qdrant_client", lambda: fake_client)

    vector_store.search([0.1, 0.2], top_k=3, category="Dev", max_price=500)

    _, kwargs = fake_client.query_points.call_args
    assert kwargs["query_filter"].must == [
        FieldCondition(key="category", match=MatchValue(value="Dev")),
        FieldCondition(key="price", range=Range(lte=500)),
    ]


def test_search_unfiltered_passes_no_filter(monkeypatch):
    fake_client = MagicMock()
    fake_client.collection_exists.return_value = True
    fake_client.query_points.return_value = SimpleNamespace(points=[])
    monkeypatch.setattr(vector_store, "get_qdrant_client", lambda: fake_client)

    vector_store.search([0.1, 0.2], top_k=3)

    _, kwargs = fake_client.query_points.call_args
    assert kwargs["query_filter"] is None

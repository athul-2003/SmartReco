import pytest
from sqlmodel import Session, select

from app.models.product import Product
from app.services import catalog


def test_create_product_dual_writes(session: Session, mock_mesh_and_qdrant):
    product = catalog.create_product(
        session, title="Intro to X", description="Learn X.", category="Dev", price=100.0
    )
    assert product.id is not None
    assert session.get(Product, product.id) is not None
    assert len(mock_mesh_and_qdrant["upserts"]) == 1
    assert mock_mesh_and_qdrant["upserts"][0][0] == product.id


def test_create_product_rolls_back_on_mesh_failure(session: Session, monkeypatch):
    def boom(texts):
        raise RuntimeError("mesh down")

    monkeypatch.setattr("app.services.catalog.embed_texts", boom)

    with pytest.raises(catalog.DualWriteError):
        catalog.create_product(
            session, title="Broken", description="x", category="Dev", price=0
        )

    remaining = session.exec(select(Product).where(Product.title == "Broken")).first()
    assert remaining is None


def test_update_product_dual_writes(session: Session, mock_mesh_and_qdrant):
    product = catalog.create_product(
        session, title="Old", description="d", category="Dev", price=10
    )
    updated = catalog.update_product(
        session, product, title="New", description="d2", category="Dev", price=20
    )
    assert updated.title == "New"
    assert len(mock_mesh_and_qdrant["upserts"]) == 2  # one from create, one from update


def test_update_product_rolls_back_on_qdrant_failure(session: Session, monkeypatch):
    fake_vector = [0.1, 0.2, 0.3]
    monkeypatch.setattr(
        "app.services.catalog.embed_texts", lambda texts: [fake_vector for _ in texts]
    )
    monkeypatch.setattr(
        "app.services.catalog.vector_store.upsert_product", lambda *a, **k: None
    )

    product = catalog.create_product(
        session, title="Stable", description="d", category="Dev", price=10
    )

    def boom(*a, **k):
        raise RuntimeError("qdrant down")

    monkeypatch.setattr("app.services.catalog.vector_store.upsert_product", boom)

    with pytest.raises(catalog.DualWriteError):
        catalog.update_product(
            session, product, title="Changed", description="d", category="Dev", price=99
        )

    session.refresh(product)
    assert product.title == "Stable"


def test_delete_product_dual_writes(session: Session, mock_mesh_and_qdrant):
    product = catalog.create_product(
        session, title="ToDelete", description="d", category="Dev", price=10
    )
    product_id = product.id

    catalog.delete_product(session, product)

    assert session.get(Product, product_id) is None
    assert product_id in mock_mesh_and_qdrant["deletes"]


def test_delete_product_aborts_on_qdrant_failure(
    session: Session, mock_mesh_and_qdrant, monkeypatch
):
    product = catalog.create_product(
        session, title="Keep", description="d", category="Dev", price=10
    )
    product_id = product.id

    def boom(product_id):
        raise RuntimeError("qdrant down")

    monkeypatch.setattr("app.services.catalog.vector_store.delete_product", boom)

    with pytest.raises(catalog.DualWriteError):
        catalog.delete_product(session, product)

    assert session.get(Product, product_id) is not None

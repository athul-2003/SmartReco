import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import get_session
from app.main import app


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_mesh_and_qdrant(monkeypatch):
    """Stands in for Mesh embeddings + Qdrant so catalog/admin tests never
    hit either real service. Records calls so tests can assert on them."""
    fake_vector = [0.1, 0.2, 0.3]
    upserts = []
    deletes = []

    monkeypatch.setattr(
        "app.services.catalog.embed_texts", lambda texts: [fake_vector for _ in texts]
    )
    monkeypatch.setattr(
        "app.services.catalog.vector_store.upsert_product",
        lambda product_id, vector, **kw: upserts.append((product_id, vector, kw)),
    )
    monkeypatch.setattr(
        "app.services.catalog.vector_store.delete_product",
        lambda product_id: deletes.append(product_id),
    )
    return {"upserts": upserts, "deletes": deletes}

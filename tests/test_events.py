from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.event import Event
from app.models.user import User


def _register(client: TestClient, email: str = "tracked@example.com") -> None:
    client.post(
        "/register",
        data={"email": email, "password": "hunter22"},
        follow_redirects=False,
    )


def test_ingest_requires_authentication(client: TestClient):
    response = client.post(
        "/events", json={"events": [{"event_type": "view", "product_id": 1}]}
    )
    assert response.status_code == 401


def test_ingest_batch_stores_events(client: TestClient, session: Session):
    _register(client)
    response = client.post(
        "/events",
        json={
            "events": [
                {"event_type": "view", "product_id": 1},
                {"event_type": "search", "metadata": {"query": "python"}},
                {"event_type": "click", "product_id": 2},
                {"event_type": "dwell", "product_id": 1, "metadata": {"seconds": 42}},
            ]
        },
    )
    assert response.status_code == 204

    rows = session.exec(select(Event)).all()
    assert len(rows) == 4
    assert {r.event_type.value for r in rows} == {"view", "search", "click", "dwell"}
    search_row = next(r for r in rows if r.event_type.value == "search")
    assert search_row.event_metadata == {"query": "python"}
    assert search_row.product_id is None
    dwell_row = next(r for r in rows if r.event_type.value == "dwell")
    assert dwell_row.event_metadata == {"seconds": 42}


def test_ingest_stamps_correct_user(client: TestClient, session: Session):
    _register(client, email="user-a@example.com")
    client.post("/events", json={"events": [{"event_type": "view", "product_id": 1}]})

    row = session.exec(select(Event)).first()
    user = session.exec(select(User).where(User.email == "user-a@example.com")).first()
    assert row.user_id == user.id


def test_ingest_rejects_empty_batch(client: TestClient):
    _register(client)
    response = client.post("/events", json={"events": []})
    assert response.status_code == 422


def test_ingest_rejects_oversized_batch(client: TestClient):
    _register(client)
    events = [{"event_type": "click", "product_id": 1} for _ in range(51)]
    response = client.post("/events", json={"events": events})
    assert response.status_code == 422


def test_ingest_rejects_invalid_event_type(client: TestClient):
    _register(client)
    response = client.post("/events", json={"events": [{"event_type": "not-a-type"}]})
    assert response.status_code == 422

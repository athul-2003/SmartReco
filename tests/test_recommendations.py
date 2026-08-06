from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.agent.triggers import EVENT_THRESHOLD
from app.models.event import Event, EventType
from app.models.product import Product
from app.models.recommendation import Recommendation
from app.models.user import User


def _register(client: TestClient, email: str = "user@example.com") -> None:
    client.post(
        "/register",
        data={"email": email, "password": "hunter22"},
        follow_redirects=False,
    )


def test_recommendations_redirects_anonymous_to_login(client: TestClient):
    response = client.get("/recommendations", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2Frecommendations"


def test_recommendations_shows_empty_state_for_logged_in_user(client: TestClient):
    _register(client)
    response = client.get("/recommendations")
    assert response.status_code == 200
    assert "Your journey starts here" in response.text


def test_recommendations_shows_generating_page_on_first_visit_with_activity(
    client: TestClient, session: Session, monkeypatch
):
    # A user who has browsed (has events) but has no recommendation yet
    # should immediately see real grounded product cards (retrieval already
    # ran) plus a placeholder that streams in the narrative via SSE - no
    # separate "generate" button/click, and no blocking on the full
    # generation before anything renders.
    product = Product(
        title="Python 101", description="Learn Python.", category="Dev", price=0
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    monkeypatch.setattr(
        "app.routers.recommendations.prepare_candidates",
        lambda s, u: (
            object(),
            [{"id": product.id, "title": product.title, "category": product.category}],
        ),
    )

    _register(client, email="active-browser@example.com")
    user = session.exec(
        select(User).where(User.email == "active-browser@example.com")
    ).first()
    session.add(
        Event(user_id=user.id, event_type=EventType.view, product_id=product.id)
    )
    session.commit()

    response = client.get("/recommendations")
    assert response.status_code == 200
    assert "Python 101" in response.text
    assert "Thinking about what fits you best" in response.text
    assert f'data-candidate-ids="{product.id}"' in response.text

    # Nothing persisted yet - only the /stream endpoint does that, once the
    # narrative finishes generating.
    recommendations = session.exec(
        select(Recommendation).where(Recommendation.user_id == user.id)
    ).all()
    assert recommendations == []


def test_recommendations_no_candidates_falls_back_immediately(
    client: TestClient, session: Session, monkeypatch
):
    # Edge case: retrieval ran but found nothing (e.g. an empty catalog).
    # No point offering to stream a narrative with no products - fall back
    # straight to the stored no-activity-yet message.
    monkeypatch.setattr(
        "app.routers.recommendations.prepare_candidates", lambda s, u: (object(), [])
    )

    _register(client, email="no-candidates@example.com")
    user = session.exec(
        select(User).where(User.email == "no-candidates@example.com")
    ).first()
    session.add(Event(user_id=user.id, event_type=EventType.view, product_id=1))
    session.commit()

    response = client.get("/recommendations")
    assert response.status_code == 200
    assert "Browse a few courses" in response.text


def test_stream_narrative_persists_recommendation(
    client: TestClient, session: Session, monkeypatch
):
    product = Product(
        title="Python 101", description="Learn Python.", category="Dev", price=0
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    def fake_stream(profile, candidates):
        yield "Great "
        yield "fit for you."

    monkeypatch.setattr(
        "app.routers.recommendations.generate_narrative_stream", fake_stream
    )
    monkeypatch.setattr(
        "app.routers.recommendations.build_profile", lambda s, u: object()
    )

    _register(client, email="streamer@example.com")
    response = client.get(f"/recommendations/stream?candidate_ids={product.id}")
    assert response.status_code == 200
    assert "data: Great " in response.text
    assert "data: fit for you." in response.text
    assert "event: done" in response.text

    user = session.exec(
        select(User).where(User.email == "streamer@example.com")
    ).first()
    recommendation = session.exec(
        select(Recommendation).where(Recommendation.user_id == user.id)
    ).first()
    assert recommendation is not None
    assert recommendation.narrative == "Great fit for you."
    assert recommendation.product_ids == [product.id]


def test_stream_narrative_requires_login(client: TestClient):
    response = client.get(
        "/recommendations/stream?candidate_ids=1", follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2Frecommendations%2Fstream"


def test_stream_narrative_sends_failed_event_and_no_partial_save_on_error(
    client: TestClient, session: Session, monkeypatch
):
    # If generation errors out before any text arrives, the stream should
    # degrade gracefully (a "failed" event, not a crashed connection) and
    # must not persist an empty/broken recommendation.
    product = Product(
        title="Python 101", description="Learn Python.", category="Dev", price=0
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    def broken_stream(profile, candidates):
        raise RuntimeError("Mesh had a bad day")
        yield  # pragma: no cover - makes this a generator function

    monkeypatch.setattr(
        "app.routers.recommendations.generate_narrative_stream", broken_stream
    )
    monkeypatch.setattr(
        "app.routers.recommendations.build_profile", lambda s, u: object()
    )

    _register(client, email="broken-stream@example.com")
    response = client.get(f"/recommendations/stream?candidate_ids={product.id}")
    assert response.status_code == 200
    assert "event: failed" in response.text

    user = session.exec(
        select(User).where(User.email == "broken-stream@example.com")
    ).first()
    recommendation = session.exec(
        select(Recommendation).where(Recommendation.user_id == user.id)
    ).first()
    assert recommendation is None


def test_stream_narrative_persists_partial_narrative_if_error_after_some_text(
    client: TestClient, session: Session, monkeypatch
):
    # If real content already streamed before a later failure, keep it -
    # better than losing genuine output and leaving the user stuck.
    product = Product(
        title="Python 101", description="Learn Python.", category="Dev", price=0
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    def partial_then_broken_stream(profile, candidates):
        yield "Partial narrative "
        raise RuntimeError("Mesh dropped mid-stream")

    monkeypatch.setattr(
        "app.routers.recommendations.generate_narrative_stream",
        partial_then_broken_stream,
    )
    monkeypatch.setattr(
        "app.routers.recommendations.build_profile", lambda s, u: object()
    )

    _register(client, email="partial-stream@example.com")
    response = client.get(f"/recommendations/stream?candidate_ids={product.id}")
    assert response.status_code == 200
    assert "event: done" in response.text

    user = session.exec(
        select(User).where(User.email == "partial-stream@example.com")
    ).first()
    recommendation = session.exec(
        select(Recommendation).where(Recommendation.user_id == user.id)
    ).first()
    assert recommendation is not None
    assert recommendation.narrative == "Partial narrative "


def test_recommendations_empty_state_links_to_catalog_categories(
    client: TestClient, session: Session
):
    session.add(
        Product(title="Python Basics", description="d", category="Dev", price=0)
    )
    session.commit()
    _register(client)

    response = client.get("/recommendations")
    assert response.status_code == 200
    assert "/catalog?category=Dev" in response.text


def test_refresh_requires_login(client: TestClient):
    response = client.post("/recommendations/refresh", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2Frecommendations%2Frefresh"


def test_refresh_creates_recommendation_and_shows_grounded_products(
    client: TestClient, session: Session, monkeypatch
):
    product = Product(
        title="Python 101", description="Learn Python.", category="Dev", price=0
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    monkeypatch.setattr(
        "app.routers.recommendations.generate_recommendation",
        lambda s, u, **kw: ("Great fit for you.", [product.id]),
    )

    _register(client)
    response = client.post("/recommendations/refresh", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/recommendations"

    view = client.get("/recommendations")
    assert view.status_code == 200
    assert "Great fit for you." in view.text
    assert "Python 101" in view.text


def test_view_recommendations_skips_ids_no_longer_in_catalog(
    client: TestClient, session: Session, monkeypatch
):
    # A stale/deleted product ID should be silently skipped, not crash or
    # render fabricated data - the display is always re-grounded against SQL.
    monkeypatch.setattr(
        "app.routers.recommendations.generate_recommendation",
        lambda s, u, **kw: ("x", [99999]),
    )
    _register(client)
    client.post("/recommendations/refresh")

    view = client.get("/recommendations")
    assert view.status_code == 200


def test_refresh_passes_category_and_max_price_filters_through(
    client: TestClient, session: Session, monkeypatch
):
    received = {}

    def fake_generate_recommendation(s, u, **kw):
        received.update(kw)
        return "x", []

    monkeypatch.setattr(
        "app.routers.recommendations.generate_recommendation",
        fake_generate_recommendation,
    )
    _register(client)
    client.post("/recommendations/refresh?category=Dev&max_price=500")

    assert received == {"category": "Dev", "max_price": 500.0}


def test_refresh_stores_manual_trigger_reason(
    client: TestClient, session: Session, monkeypatch
):
    monkeypatch.setattr(
        "app.routers.recommendations.generate_recommendation",
        lambda s, u, **kw: ("x", []),
    )
    _register(client)
    client.post("/recommendations/refresh")

    user = session.exec(select(User).where(User.email == "user@example.com")).first()
    recommendation = session.exec(
        select(Recommendation).where(Recommendation.user_id == user.id)
    ).first()
    assert recommendation.trigger_reason == "manual"


def test_view_recommendations_serves_cache_below_event_threshold(
    client: TestClient, session: Session, monkeypatch
):
    # Phase 5: a cached recommendation should keep being served - no Mesh
    # call - until enough new activity has landed to make regenerating
    # worthwhile.
    def _boom(s, u):
        raise AssertionError("prepare_candidates should not run below threshold")

    monkeypatch.setattr("app.routers.recommendations.prepare_candidates", _boom)

    _register(client, email="cached@example.com")
    user = session.exec(select(User).where(User.email == "cached@example.com")).first()
    session.add(
        Recommendation(
            user_id=user.id,
            narrative="Cached narrative.",
            product_ids=[],
            created_at=datetime.now(UTC) - timedelta(minutes=5),
        )
    )
    for _ in range(EVENT_THRESHOLD - 1):
        session.add(Event(user_id=user.id, event_type=EventType.view))
    session.commit()

    response = client.get("/recommendations")
    assert response.status_code == 200
    assert "Cached narrative." in response.text


def test_view_recommendations_auto_regenerates_at_event_threshold(
    client: TestClient, session: Session, monkeypatch
):
    product = Product(title="Advanced Python", description="d", category="Dev", price=0)
    session.add(product)
    session.commit()
    session.refresh(product)

    monkeypatch.setattr(
        "app.routers.recommendations.prepare_candidates",
        lambda s, u: (
            object(),
            [{"id": product.id, "title": product.title, "category": product.category}],
        ),
    )

    _register(client, email="threshold@example.com")
    user = session.exec(
        select(User).where(User.email == "threshold@example.com")
    ).first()
    session.add(
        Recommendation(
            user_id=user.id,
            narrative="Stale narrative.",
            product_ids=[],
            created_at=datetime.now(UTC) - timedelta(minutes=5),
        )
    )
    for _ in range(EVENT_THRESHOLD):
        session.add(Event(user_id=user.id, event_type=EventType.view))
    session.commit()

    response = client.get("/recommendations")
    assert response.status_code == 200
    assert "Advanced Python" in response.text
    assert 'data-trigger-reason="threshold"' in response.text
    assert "Stale narrative." not in response.text


def test_stream_narrative_persists_threshold_trigger_reason(
    client: TestClient, session: Session, monkeypatch
):
    product = Product(title="Python 101", description="d", category="Dev", price=0)
    session.add(product)
    session.commit()
    session.refresh(product)

    def fake_stream(profile, candidates):
        yield "Fresh take."

    monkeypatch.setattr(
        "app.routers.recommendations.generate_narrative_stream", fake_stream
    )
    monkeypatch.setattr(
        "app.routers.recommendations.build_profile", lambda s, u: object()
    )

    _register(client, email="threshold-stream@example.com")
    client.get(f"/recommendations/stream?candidate_ids={product.id}&reason=threshold")

    user = session.exec(
        select(User).where(User.email == "threshold-stream@example.com")
    ).first()
    recommendation = session.exec(
        select(Recommendation).where(Recommendation.user_id == user.id)
    ).first()
    assert recommendation.trigger_reason == "threshold"

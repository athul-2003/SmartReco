from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.product import Product


def _register(client: TestClient, email: str = "user@example.com") -> None:
    client.post(
        "/register",
        data={"email": email, "password": "hunter22"},
        follow_redirects=False,
    )


def test_recommendations_redirects_anonymous_to_login(client: TestClient):
    response = client.get("/recommendations", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_recommendations_shows_empty_state_for_logged_in_user(client: TestClient):
    _register(client)
    response = client.get("/recommendations")
    assert response.status_code == 200
    assert "Your journey starts here" in response.text


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
    assert response.headers["location"] == "/login"


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
        lambda s, u: ("Great fit for you.", [product.id]),
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
        lambda s, u: ("x", [99999]),
    )
    _register(client)
    client.post("/recommendations/refresh")

    view = client.get("/recommendations")
    assert view.status_code == 200

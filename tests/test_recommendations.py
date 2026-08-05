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

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.product import Product


def _add_product(session: Session, **kwargs) -> Product:
    defaults = {
        "title": "Sample Course",
        "description": "A sample.",
        "category": "Dev",
        "price": 0.0,
    }
    defaults.update(kwargs)
    product = Product(**defaults)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def test_browse_lists_products(client: TestClient, session: Session):
    _add_product(session, title="Python Basics", category="Dev")
    response = client.get("/catalog")
    assert response.status_code == 200
    assert "Python Basics" in response.text


def test_browse_search_filters_by_query(client: TestClient, session: Session):
    _add_product(session, title="Python Basics", category="Dev")
    _add_product(session, title="Yoga for Beginners", category="Lifestyle")
    response = client.get("/catalog", params={"q": "Python"})
    assert "Python Basics" in response.text
    assert "Yoga for Beginners" not in response.text


def test_browse_filters_by_category(client: TestClient, session: Session):
    _add_product(session, title="Python Basics", category="Dev")
    _add_product(session, title="Yoga for Beginners", category="Lifestyle")
    response = client.get("/catalog", params={"category": "Lifestyle"})
    assert "Yoga for Beginners" in response.text
    assert "Python Basics" not in response.text


def test_detail_shows_product(client: TestClient, session: Session):
    product = _add_product(
        session, title="Deep Dive", description="Long description here."
    )
    response = client.get(f"/catalog/{product.id}")
    assert response.status_code == 200
    assert "Deep Dive" in response.text
    assert "Long description here." in response.text


def test_detail_404_for_missing_product(client: TestClient):
    response = client.get("/catalog/99999")
    assert response.status_code == 404

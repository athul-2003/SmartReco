from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.product import Product
from app.models.user import Role, User


def _register_and_promote(
    client: TestClient, session: Session, email: str = "admin@example.com"
) -> None:
    client.post(
        "/register",
        data={"email": email, "password": "hunter22"},
        follow_redirects=False,
    )
    user = session.exec(select(User).where(User.email == email)).first()
    user.role = Role.admin
    session.add(user)
    session.commit()


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


def test_non_admin_cannot_access_product_admin(client: TestClient):
    client.post(
        "/register",
        data={"email": "user@example.com", "password": "hunter22"},
        follow_redirects=False,
    )
    response = client.get("/admin/products", follow_redirects=False)
    assert response.status_code == 403


def test_admin_can_create_product(
    client: TestClient, session: Session, mock_mesh_and_qdrant
):
    _register_and_promote(client, session)

    response = client.post(
        "/admin/products/new",
        data={
            "title": "New Course",
            "description": "Learn things.",
            "category": "Dev",
            "price": "100",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    product = session.exec(select(Product).where(Product.title == "New Course")).first()
    assert product is not None
    assert len(mock_mesh_and_qdrant["upserts"]) == 1


def test_admin_can_edit_product(
    client: TestClient, session: Session, mock_mesh_and_qdrant
):
    _register_and_promote(client, session)
    client.post(
        "/admin/products/new",
        data={
            "title": "Old Title",
            "description": "d",
            "category": "Dev",
            "price": "10",
        },
    )
    product = session.exec(select(Product).where(Product.title == "Old Title")).first()

    response = client.post(
        f"/admin/products/{product.id}/edit",
        data={
            "title": "Updated Title",
            "description": "d2",
            "category": "Dev",
            "price": "20",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    session.refresh(product)
    assert product.title == "Updated Title"


def test_admin_can_delete_product(
    client: TestClient, session: Session, mock_mesh_and_qdrant
):
    _register_and_promote(client, session)
    client.post(
        "/admin/products/new",
        data={
            "title": "ToDelete",
            "description": "d",
            "category": "Dev",
            "price": "10",
        },
    )
    product = session.exec(select(Product).where(Product.title == "ToDelete")).first()
    product_id = product.id

    response = client.post(
        f"/admin/products/{product_id}/delete", follow_redirects=False
    )
    assert response.status_code == 303
    assert session.get(Product, product_id) is None
    assert product_id in mock_mesh_and_qdrant["deletes"]


def test_edit_nonexistent_product_404s(client: TestClient, session: Session):
    _register_and_promote(client, session)
    response = client.get("/admin/products/99999/edit")
    assert response.status_code == 404


def test_list_products_search_filters_by_query(client: TestClient, session: Session):
    _register_and_promote(client, session)
    _add_product(session, title="Python Basics", category="Dev")
    _add_product(session, title="Yoga for Beginners", category="Lifestyle")

    response = client.get("/admin/products", params={"q": "Python"})
    assert "Python Basics" in response.text
    assert "Yoga for Beginners" not in response.text


def test_list_products_filters_by_category(client: TestClient, session: Session):
    _register_and_promote(client, session)
    _add_product(session, title="Python Basics", category="Dev")
    _add_product(session, title="Yoga for Beginners", category="Lifestyle")

    response = client.get("/admin/products", params={"category": "Lifestyle"})
    assert "Yoga for Beginners" in response.text
    assert "Python Basics" not in response.text


def test_list_products_paginates(client: TestClient, session: Session, monkeypatch):
    _register_and_promote(client, session)
    monkeypatch.setattr("app.routers.admin.PAGE_SIZE", 1)
    _add_product(session, title="Course A", category="Dev")
    _add_product(session, title="Course B", category="Dev")

    first_page = client.get("/admin/products")
    assert first_page.status_code == 200
    assert "Showing 1" in first_page.text
    assert 'aria-label="Course management pages"' in first_page.text

    second_page = client.get("/admin/products", params={"page": 2})
    assert second_page.status_code == 200
    assert "Showing 2" in second_page.text

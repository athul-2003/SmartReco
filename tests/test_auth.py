from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.user import Role, User


def register(
    client: TestClient, email: str = "user@example.com", password: str = "hunter22"
):
    return client.post(
        "/register",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def test_register_creates_user_and_starts_session(client: TestClient):
    response = register(client)
    assert response.status_code == 303
    assert response.headers["location"] == "/catalog"

    home = client.get("/")
    assert "user@example.com" in home.text


def test_register_duplicate_email_rejected(client: TestClient):
    register(client)
    response = register(client)
    assert response.status_code == 400
    assert "already exists" in response.text


def test_login_wrong_password_rejected(client: TestClient):
    register(client)
    client.post("/logout", follow_redirects=False)

    response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "wrong-password"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Incorrect email or password" in response.text


def test_login_success_after_logout(client: TestClient):
    register(client)
    client.post("/logout", follow_redirects=False)

    response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "hunter22"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    home = client.get("/")
    assert "user@example.com" in home.text


def test_logout_clears_session(client: TestClient):
    register(client)
    client.post("/logout", follow_redirects=False)

    home = client.get("/")
    assert "user@example.com" not in home.text
    assert 'href="/login"' in home.text


def test_admin_route_redirects_anonymous_to_login(client: TestClient):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_admin_route_forbidden_for_regular_user(client: TestClient):
    register(client)
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 403


def test_admin_route_allowed_for_admin_user(client: TestClient, session: Session):
    register(client)
    user = session.exec(select(User).where(User.email == "user@example.com")).first()
    user.role = Role.admin
    session.add(user)
    session.commit()

    response = client.get("/admin")
    assert response.status_code == 200
    assert "Course Management" in response.text

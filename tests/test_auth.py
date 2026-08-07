from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.user import Role, User
from app.services.auth import safe_next_path


def test_safe_next_path_allows_relative_paths():
    assert safe_next_path("/recommendations") == "/recommendations"
    assert safe_next_path("/catalog/42") == "/catalog/42"


def test_safe_next_path_rejects_missing_or_empty():
    assert safe_next_path(None) == "/catalog"
    assert safe_next_path("") == "/catalog"


def test_safe_next_path_rejects_absolute_and_protocol_relative_urls():
    assert safe_next_path("https://evil.example.com") == "/catalog"
    assert safe_next_path("//evil.example.com") == "/catalog"
    assert safe_next_path("javascript:alert(1)") == "/catalog"


def test_safe_next_path_uses_custom_default():
    assert safe_next_path(None, default="/admin") == "/admin"
    assert safe_next_path("//evil.example.com", default="/admin") == "/admin"
    # An explicit valid next still wins over a custom default.
    assert safe_next_path("/recommendations", default="/admin") == "/recommendations"


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
    assert response.headers["location"] == "/login?next=%2Fadmin"


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


def test_login_lands_admin_on_dashboard_by_default(
    client: TestClient, session: Session
):
    register(client, email="admin-login@example.com")
    user = session.exec(
        select(User).where(User.email == "admin-login@example.com")
    ).first()
    user.role = Role.admin
    session.add(user)
    session.commit()
    client.post("/logout", follow_redirects=False)

    response = client.post(
        "/login",
        data={"email": "admin-login@example.com", "password": "hunter22"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"


def test_login_still_respects_next_for_admin(client: TestClient, session: Session):
    # The role-based default only applies when there's no explicit next -
    # an admin following a login-gated link should still land there.
    register(client, email="admin-next@example.com")
    user = session.exec(
        select(User).where(User.email == "admin-next@example.com")
    ).first()
    user.role = Role.admin
    session.add(user)
    session.commit()
    client.post("/logout", follow_redirects=False)

    response = client.post(
        "/login",
        data={
            "email": "admin-next@example.com",
            "password": "hunter22",
            "next": "/recommendations",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/recommendations"


def test_home_redirects_admin_to_dashboard(client: TestClient, session: Session):
    register(client, email="admin-home@example.com")
    user = session.exec(
        select(User).where(User.email == "admin-home@example.com")
    ).first()
    user.role = Role.admin
    session.add(user)
    session.commit()

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"


def test_home_redirects_regular_user_to_catalog(client: TestClient):
    register(client)
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/catalog"


def test_login_redirects_to_next_after_success(client: TestClient):
    # A user who followed a login-gated link (e.g. a digest email's "View
    # in Dashboard" button) should land there after signing in, not on the
    # generic post-login /catalog page.
    register(client)
    client.post("/logout", follow_redirects=False)

    response = client.post(
        "/login",
        data={
            "email": "user@example.com",
            "password": "hunter22",
            "next": "/recommendations",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/recommendations"


def test_login_form_renders_next_as_hidden_field(client: TestClient):
    response = client.get("/login?next=/recommendations")
    assert 'name="next" value="/recommendations"' in response.text


def test_register_redirects_to_next_after_success(client: TestClient):
    response = client.post(
        "/register",
        data={
            "email": "newbie@example.com",
            "password": "hunter22",
            "next": "/recommendations",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/recommendations"


def test_login_rejects_offsite_next_as_open_redirect(client: TestClient):
    register(client)
    client.post("/logout", follow_redirects=False)

    response = client.post(
        "/login",
        data={
            "email": "user@example.com",
            "password": "hunter22",
            "next": "https://evil.example.com",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/catalog"


def test_login_rejects_protocol_relative_next(client: TestClient):
    register(client)
    client.post("/logout", follow_redirects=False)

    response = client.post(
        "/login",
        data={
            "email": "user@example.com",
            "password": "hunter22",
            "next": "//evil.example.com",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/catalog"


def test_full_login_gated_link_flow_lands_on_recommendations(client: TestClient):
    # End-to-end: anonymous visit to a login-gated link (like the digest
    # email's dashboard button) -> redirected to login with `next` set ->
    # after signing in, lands exactly where they were headed.
    register(client)
    client.post("/logout", follow_redirects=False)

    gated = client.get("/recommendations", follow_redirects=False)
    assert gated.status_code == 303
    login_url = gated.headers["location"]
    assert login_url == "/login?next=%2Frecommendations"

    login_page = client.get(login_url)
    assert 'name="next" value="/recommendations"' in login_page.text

    logged_in = client.post(
        "/login",
        data={
            "email": "user@example.com",
            "password": "hunter22",
            "next": "/recommendations",
        },
        follow_redirects=False,
    )
    assert logged_in.headers["location"] == "/recommendations"

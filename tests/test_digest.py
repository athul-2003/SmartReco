import logging

from sqlmodel import Session

from app.models.event import Event, EventType
from app.models.product import Product
from app.models.user import User
from app.services import digest
from app.services.auth import hash_password

BASE_URL = "https://smartreco.example.com"


def _make_user(session: Session, email: str = "learner@example.com") -> User:
    user = User(email=email, password_hash=hash_password("hunter22"))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_run_daily_digest_emails_active_users_only(session: Session, monkeypatch):
    active = _make_user(session, "active@example.com")
    _make_user(session, "inactive@example.com")
    session.add(Event(user_id=active.id, event_type=EventType.view))
    session.commit()

    product = Product(title="Python 101", description="d", category="Dev", price=0)
    session.add(product)
    session.commit()
    session.refresh(product)

    monkeypatch.setattr(
        digest,
        "run_recommendation_graph",
        lambda s, u: ("Great picks.", [product.id]),
    )
    sent_to = []
    monkeypatch.setattr(
        digest, "send_email", lambda to, subject, body, **kw: sent_to.append(to)
    )

    count = digest.run_daily_digest(session)

    assert count == 1
    assert sent_to == ["active@example.com"]


def test_run_daily_digest_skips_users_with_no_grounded_recommendations(
    session: Session, monkeypatch
):
    user = _make_user(session)
    session.add(Event(user_id=user.id, event_type=EventType.view))
    session.commit()

    monkeypatch.setattr(digest, "run_recommendation_graph", lambda s, u: ("x", []))
    sent_to = []
    monkeypatch.setattr(
        digest, "send_email", lambda to, subject, body, **kw: sent_to.append(to)
    )

    count = digest.run_daily_digest(session)

    assert count == 0
    assert sent_to == []


def test_run_daily_digest_logs_progress_per_sent_email(
    session: Session, monkeypatch, caplog
):
    # Each user runs a real LangGraph pipeline (Mesh + Qdrant calls), so a
    # digest run across many users takes a while - without this, a manual
    # `make digest` run (or the real scheduled job) shows nothing at all
    # until the very end, indistinguishable from a hang.
    user = _make_user(session, "progress@example.com")
    session.add(Event(user_id=user.id, event_type=EventType.view))
    session.commit()

    product = Product(title="Python 101", description="d", category="Dev", price=0)
    session.add(product)
    session.commit()
    session.refresh(product)

    monkeypatch.setattr(
        digest,
        "run_recommendation_graph",
        lambda s, u: ("Great picks.", [product.id]),
    )
    monkeypatch.setattr(digest, "send_email", lambda *a, **kw: None)

    with caplog.at_level(logging.INFO, logger="app.services.digest"):
        count = digest.run_daily_digest(session)

    assert count == 1
    assert "1/1: sent to progress@example.com" in caplog.text
    assert "Digest complete: 1/1" in caplog.text


def test_run_daily_digest_logs_skip_for_no_grounded_candidates(
    session: Session, monkeypatch, caplog
):
    user = _make_user(session)
    session.add(Event(user_id=user.id, event_type=EventType.view))
    session.commit()

    monkeypatch.setattr(digest, "run_recommendation_graph", lambda s, u: ("x", []))

    with caplog.at_level(logging.INFO, logger="app.services.digest"):
        count = digest.run_daily_digest(session)

    assert count == 0
    assert f"skipping user_id={user.id}" in caplog.text


def test_render_digest_email_includes_narrative_and_products():
    product = Product(
        id=1, title="Python 101", description="d", category="Dev", price=1500
    )
    body = digest.render_digest_email("Because you like Dev.", [product], BASE_URL)
    assert "Because you like Dev." in body
    assert "Python 101" in body
    assert "Dev" in body
    assert "INR 1500.00" in body


def test_render_digest_email_marks_free_products():
    product = Product(
        id=1, title="Intro to X", description="d", category="Dev", price=0
    )
    body = digest.render_digest_email("Narrative.", [product], BASE_URL)
    assert "Free" in body


def test_render_digest_email_includes_course_and_dashboard_links():
    product = Product(
        id=42, title="Intro to X", description="d", category="Dev", price=0
    )
    body = digest.render_digest_email("Narrative.", [product], BASE_URL)
    assert f"{BASE_URL}/catalog/42" in body
    assert f"{BASE_URL}/recommendations" in body


def test_render_digest_email_frames_narrative_as_personalized():
    # Reads clearly as "picked for you based on recent activity", not just
    # the raw narrative sentence with no context.
    product = Product(
        id=1, title="Intro to X", description="d", category="Dev", price=0
    )
    body = digest.render_digest_email("Narrative.", [product], BASE_URL)
    assert "Based on your recent activity" in body
    assert "chosen specifically for you" in body


def test_render_digest_email_html_frames_narrative_as_personalized():
    product = Product(
        id=1, title="Intro to X", description="d", category="Dev", price=0
    )
    html = digest.render_digest_email_html("Narrative.", [product], BASE_URL)
    assert "Based on your recent activity" in html
    assert "chosen specifically for you" in html


def test_render_digest_email_html_includes_narrative_and_products():
    product = Product(
        id=1, title="Python 101", description="d", category="Dev", price=1500
    )
    html = digest.render_digest_email_html("Because you like Dev.", [product], BASE_URL)
    assert "Because you like Dev." in html
    assert "Python 101" in html
    assert "Dev" in html
    assert "&#8377;1,500.00" in html
    assert html.strip().startswith("<!doctype html>")


def test_render_digest_email_html_marks_free_products():
    product = Product(
        id=1, title="Intro to X", description="d", category="Dev", price=0
    )
    html = digest.render_digest_email_html("Narrative.", [product], BASE_URL)
    assert "Free" in html


def test_render_digest_email_html_links_each_course_to_its_detail_page():
    product = Product(
        id=42, title="Intro to X", description="d", category="Dev", price=0
    )
    html = digest.render_digest_email_html("Narrative.", [product], BASE_URL)
    assert f'href="{BASE_URL}/catalog/42"' in html


def test_render_digest_email_html_includes_dashboard_button():
    product = Product(
        id=1, title="Intro to X", description="d", category="Dev", price=0
    )
    html = digest.render_digest_email_html("Narrative.", [product], BASE_URL)
    assert f'href="{BASE_URL}/recommendations"' in html
    assert "View in Dashboard" in html


def test_render_digest_email_html_escapes_untrusted_content():
    # Narrative comes from Mesh, titles/categories from the catalog - none
    # of it should be trusted to already be safe HTML.
    product = Product(
        id=1,
        title="<b>Bold</b> Title",
        description="d",
        category="<i>Dev</i>",
        price=0,
    )
    html = digest.render_digest_email_html(
        "<script>evil()</script>", [product], BASE_URL
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<b>Bold</b>" not in html
    assert "&lt;b&gt;Bold&lt;/b&gt;" in html


def test_run_daily_digest_sends_html_alternative(session: Session, monkeypatch):
    user = _make_user(session, "html@example.com")
    session.add(Event(user_id=user.id, event_type=EventType.view))
    session.commit()

    product = Product(title="Python 101", description="d", category="Dev", price=0)
    session.add(product)
    session.commit()
    session.refresh(product)

    monkeypatch.setattr(
        digest,
        "run_recommendation_graph",
        lambda s, u: ("Great picks.", [product.id]),
    )
    calls = []
    monkeypatch.setattr(
        digest,
        "send_email",
        lambda to, subject, body, **kw: calls.append(kw),
    )

    digest.run_daily_digest(session)

    assert len(calls) == 1
    assert "html_body" in calls[0]
    assert calls[0]["html_body"].strip().startswith("<!doctype html>")


def test_run_daily_digest_uses_configured_public_base_url(
    session: Session, monkeypatch
):
    user = _make_user(session, "baseurl@example.com")
    session.add(Event(user_id=user.id, event_type=EventType.view))
    session.commit()

    product = Product(title="Python 101", description="d", category="Dev", price=0)
    session.add(product)
    session.commit()
    session.refresh(product)

    monkeypatch.setattr(
        digest,
        "run_recommendation_graph",
        lambda s, u: ("Great picks.", [product.id]),
    )
    monkeypatch.setattr(
        digest,
        "get_settings",
        lambda: type("S", (), {"public_base_url": "https://real.smartreco.app"})(),
    )
    calls = []
    monkeypatch.setattr(
        digest, "send_email", lambda to, subject, body, **kw: calls.append((body, kw))
    )

    digest.run_daily_digest(session)

    body, kw = calls[0]
    assert "https://real.smartreco.app/recommendations" in body
    assert f"https://real.smartreco.app/catalog/{product.id}" in body
    assert "https://real.smartreco.app/recommendations" in kw["html_body"]

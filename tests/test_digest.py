from sqlmodel import Session

from app.models.event import Event, EventType
from app.models.product import Product
from app.models.user import User
from app.services import digest
from app.services.auth import hash_password


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
        digest, "send_email", lambda to, subject, body: sent_to.append(to)
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
        digest, "send_email", lambda to, subject, body: sent_to.append(to)
    )

    count = digest.run_daily_digest(session)

    assert count == 0
    assert sent_to == []


def test_render_digest_email_includes_narrative_and_products():
    product = Product(
        id=1, title="Python 101", description="d", category="Dev", price=1500
    )
    body = digest.render_digest_email("Because you like Dev.", [product])
    assert "Because you like Dev." in body
    assert "Python 101" in body
    assert "Dev" in body
    assert "INR 1500.00" in body


def test_render_digest_email_marks_free_products():
    product = Product(
        id=1, title="Intro to X", description="d", category="Dev", price=0
    )
    body = digest.render_digest_email("Narrative.", [product])
    assert "Free" in body

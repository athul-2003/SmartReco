from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.agent.triggers import EVENT_THRESHOLD, should_auto_regenerate
from app.models.event import Event, EventType
from app.models.recommendation import Recommendation
from app.models.user import User


def _make_user(session: Session, email: str = "trigger@example.com") -> User:
    user = User(email=email, password_hash="x")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_recommendation(
    session: Session, user: User, minutes_ago: int = 5
) -> Recommendation:
    recommendation = Recommendation(
        user_id=user.id,
        narrative="n",
        product_ids=[],
        created_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
    )
    session.add(recommendation)
    session.commit()
    session.refresh(recommendation)
    return recommendation


def _add_events(session: Session, user: User, count: int, minutes_ago: int = 0) -> None:
    created_at = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    for _ in range(count):
        session.add(
            Event(user_id=user.id, event_type=EventType.view, created_at=created_at)
        )
    session.commit()


def test_should_not_auto_regenerate_below_threshold(session: Session):
    user = _make_user(session)
    recommendation = _make_recommendation(session, user)
    _add_events(session, user, EVENT_THRESHOLD - 1)

    assert should_auto_regenerate(session, user, recommendation) is False


def test_should_auto_regenerate_at_threshold(session: Session):
    user = _make_user(session)
    recommendation = _make_recommendation(session, user)
    _add_events(session, user, EVENT_THRESHOLD)

    assert should_auto_regenerate(session, user, recommendation) is True


def test_should_auto_regenerate_ignores_events_before_recommendation(
    session: Session,
):
    # Events that predate the cached recommendation already informed it -
    # only genuinely new activity since then should count toward the
    # threshold.
    user = _make_user(session)
    _add_events(session, user, EVENT_THRESHOLD, minutes_ago=10)
    recommendation = _make_recommendation(session, user, minutes_ago=5)

    assert should_auto_regenerate(session, user, recommendation) is False


def test_should_auto_regenerate_ignores_other_users_events(session: Session):
    user = _make_user(session, email="a@example.com")
    other = _make_user(session, email="b@example.com")
    recommendation = _make_recommendation(session, user)
    _add_events(session, other, EVENT_THRESHOLD)

    assert should_auto_regenerate(session, user, recommendation) is False

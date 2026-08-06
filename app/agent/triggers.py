"""
Phase 5: hybrid regeneration trigger. `GET /recommendations` must not call
Mesh on every page view (NFR "Efficiency") - it should keep serving the
cached `Recommendation` row until either enough new behavior has
accumulated to make regenerating meaningful, or the user asks for it
directly via the manual refresh button.
"""

from sqlmodel import Session, func, select

from app.models.event import Event
from app.models.recommendation import Recommendation
from app.models.user import User

EVENT_THRESHOLD = 5


def new_event_count_since(
    session: Session, user: User, recommendation: Recommendation
) -> int:
    return session.exec(
        select(func.count())
        .select_from(Event)
        .where(Event.user_id == user.id)
        .where(Event.created_at > recommendation.created_at)
    ).one()


def should_auto_regenerate(
    session: Session, user: User, recommendation: Recommendation
) -> bool:
    """True once EVENT_THRESHOLD qualifying events have landed since the
    given recommendation was generated. Callers handle the "no
    recommendation yet" case separately (cold-start/first-generation), not
    through this trigger."""
    return new_event_count_since(session, user, recommendation) >= EVENT_THRESHOLD

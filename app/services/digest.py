"""
Phase 6 bonus (FR-6): the daily digest job's logic - runs the same
recommendation pipeline used by the manual refresh button (agent/graph.py)
for every active user, and emails each of them the result. Kept separate
from scheduler.py so tests can invoke run_daily_digest() directly against a
real Session, without needing to run the actual APScheduler loop (per
CLAUDE.md's testing bar for this phase).
"""

from sqlmodel import Session, select

from app.agent.graph import run_recommendation_graph
from app.models.event import Event
from app.models.product import Product
from app.models.user import User
from app.services.email import send_email

DIGEST_SUBJECT = "Your SmartReco picks for today"


def _active_user_ids(session: Session) -> list[int]:
    """Active = has tracked at least one behavioral event - nothing to
    recommend from otherwise, matching the same premise as the cold-start
    empty state on GET /recommendations."""
    return list(session.exec(select(Event.user_id).distinct()).all())


def _ordered_products(session: Session, product_ids: list[int]) -> list[Product]:
    products = session.exec(select(Product).where(Product.id.in_(product_ids))).all()
    by_id = {p.id: p for p in products}
    return [by_id[pid] for pid in product_ids if pid in by_id]


def render_digest_email(narrative: str, products: list[Product]) -> str:
    lines = [narrative, "", "Recommended for you:"]
    for product in products:
        price = "Free" if product.price == 0 else f"INR {product.price:.2f}"
        lines.append(f"- {product.title} ({product.category}) - {price}")
    return "\n".join(lines)


def run_daily_digest(session: Session) -> int:
    """Runs the pipeline for every active user and emails a digest. Returns
    the number of digests actually sent (users with no grounded
    recommendations are skipped, not emailed an empty one)."""
    sent = 0
    for user_id in _active_user_ids(session):
        user = session.get(User, user_id)
        if user is None:
            continue

        narrative, product_ids = run_recommendation_graph(session, user)
        if not product_ids:
            continue

        products = _ordered_products(session, product_ids)
        body = render_digest_email(narrative, products)
        send_email(user.email, DIGEST_SUBJECT, body)
        sent += 1

    return sent

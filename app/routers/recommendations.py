from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.agent.nodes import generate_recommendation
from app.db import get_session
from app.models.event import Event
from app.models.product import Product
from app.models.recommendation import Recommendation
from app.models.user import User
from app.services.auth import require_login
from app.services.ui import category_cover

router = APIRouter(prefix="/recommendations")
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["cover"] = category_cover

STARTING_POINTS_LIMIT = 3


def _latest_recommendation(session: Session, user: User) -> Recommendation | None:
    return session.exec(
        select(Recommendation)
        .where(Recommendation.user_id == user.id)
        .order_by(Recommendation.created_at.desc())
    ).first()


def _has_activity(session: Session, user: User) -> bool:
    return (
        session.exec(select(Event.id).where(Event.user_id == user.id).limit(1)).first()
        is not None
    )


def _generate_and_store(
    session: Session, user: User, trigger_reason: str
) -> Recommendation:
    narrative, product_ids = generate_recommendation(session, user)
    recommendation = Recommendation(
        user_id=user.id,
        narrative=narrative,
        product_ids=product_ids,
        trigger_reason=trigger_reason,
    )
    session.add(recommendation)
    session.commit()
    session.refresh(recommendation)
    return recommendation


@router.get("", response_class=HTMLResponse)
def view_recommendations(
    request: Request,
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    recommendation = _latest_recommendation(session, user)

    if recommendation is None:
        if _has_activity(session, user):
            # First visit with real behavior to draw on - generate right
            # away rather than making the user click a separate button
            # just to see what they already have data for.
            recommendation = _generate_and_store(session, user, "manual")
        else:
            categories = session.exec(
                select(Product.category)
                .distinct()
                .order_by(Product.category)
                .limit(STARTING_POINTS_LIMIT)
            ).all()
            return templates.TemplateResponse(
                request,
                "recommendations/empty.html",
                {"user": user, "categories": categories},
            )

    products = session.exec(
        select(Product).where(Product.id.in_(recommendation.product_ids))
    ).all()
    products_by_id = {p.id: p for p in products}
    # Preserve the agent's ranked order - .in_() doesn't guarantee it.
    ordered_products = [
        products_by_id[pid]
        for pid in recommendation.product_ids
        if pid in products_by_id
    ]

    return templates.TemplateResponse(
        request,
        "recommendations/view.html",
        {"user": user, "recommendation": recommendation, "products": ordered_products},
    )


@router.post("/refresh")
def refresh_recommendations(
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    _generate_and_store(session, user, "manual")
    return RedirectResponse(url="/recommendations", status_code=303)

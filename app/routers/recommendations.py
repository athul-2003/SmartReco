from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.agent.nodes import (
    NO_ACTIVITY_NARRATIVE,
    build_profile,
    generate_narrative_stream,
    generate_recommendation,
    prepare_candidates,
)
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


def _ordered_products(session: Session, product_ids: list[int]) -> list[Product]:
    products = session.exec(select(Product).where(Product.id.in_(product_ids))).all()
    products_by_id = {p.id: p for p in products}
    # Preserve the agent's ranked order - .in_() doesn't guarantee it.
    return [products_by_id[pid] for pid in product_ids if pid in products_by_id]


def _store_recommendation(
    session: Session, user: User, narrative: str, product_ids: list[int]
) -> Recommendation:
    recommendation = Recommendation(
        user_id=user.id,
        narrative=narrative,
        product_ids=product_ids,
        trigger_reason="manual",
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
        if not _has_activity(session, user):
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

        # First visit with real behavior to draw on. Retrieval only (~1-2s,
        # one Mesh embed call + Qdrant) so we can show real grounded product
        # cards immediately; the slower narrative streams in separately
        # rather than blocking this whole page load (see /stream below).
        _, candidates = prepare_candidates(session, user)
        if not candidates:
            recommendation = _store_recommendation(
                session, user, NO_ACTIVITY_NARRATIVE, []
            )
        else:
            candidate_ids = [c["id"] for c in candidates]
            products = _ordered_products(session, candidate_ids)
            return templates.TemplateResponse(
                request,
                "recommendations/generating.html",
                {
                    "user": user,
                    "products": products,
                    "candidate_ids": ",".join(str(pid) for pid in candidate_ids),
                },
            )

    ordered_products = _ordered_products(session, recommendation.product_ids)
    return templates.TemplateResponse(
        request,
        "recommendations/view.html",
        {"user": user, "recommendation": recommendation, "products": ordered_products},
    )


@router.get("/stream")
def stream_narrative(
    candidate_ids: str,
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    """Server-Sent Events: streams the narrative for the product IDs already
    retrieved and shown by the initial page load (see view_recommendations
    above), then persists the finished Recommendation. Re-derives the
    profile (cheap, no Mesh call) but does not re-embed/re-retrieve - that
    already happened once, in the request that rendered generating.html."""
    product_ids = [int(pid) for pid in candidate_ids.split(",") if pid]
    products = _ordered_products(session, product_ids)
    candidates = [
        {"id": p.id, "title": p.title, "category": p.category} for p in products
    ]

    def event_stream():
        if not candidates:
            yield "event: done\ndata: \n\n"
            return

        profile = build_profile(session, user)
        chunks: list[str] = []
        for chunk in generate_narrative_stream(profile, candidates):
            chunks.append(chunk)
            yield "data: " + chunk.replace("\n", "\ndata: ") + "\n\n"

        narrative = "".join(chunks)
        _store_recommendation(session, user, narrative, product_ids)
        yield "event: done\ndata: \n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/refresh")
def refresh_recommendations(
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    narrative, product_ids = generate_recommendation(session, user)
    _store_recommendation(session, user, narrative, product_ids)
    return RedirectResponse(url="/recommendations", status_code=303)

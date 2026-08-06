import logging
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.agent.graph import run_recommendation_graph as generate_recommendation
from app.agent.nodes import (
    NO_ACTIVITY_NARRATIVE,
    build_profile,
    generate_narrative_stream,
    prepare_candidates,
)
from app.agent.triggers import should_auto_regenerate
from app.db import get_session
from app.models.event import Event
from app.models.product import Product
from app.models.recommendation import Recommendation
from app.models.user import User
from app.services.auth import require_login
from app.services.ui import category_cover

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations")
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["cover"] = category_cover

STARTING_POINTS_LIMIT = 3

REFRESH_ERROR_MESSAGES = {
    "refresh_failed": (
        "We couldn't refresh your recommendations just now - please try again "
        "in a moment."
    ),
}


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
    session: Session,
    user: User,
    narrative: str,
    product_ids: list[int],
    trigger_reason: str = "manual",
) -> Recommendation:
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


def _render_generating(
    request: Request, session: Session, user: User, trigger_reason: str
) -> HTMLResponse | None:
    """Runs retrieval (the fast part) and renders generating.html with real
    grounded product cards plus a placeholder that streams the narrative in
    via /stream. Returns None if retrieval found no candidates, so callers
    can decide how to handle that (differs between first-generation and the
    auto-regenerate trigger)."""
    _, candidates = prepare_candidates(session, user)
    if not candidates:
        return None
    candidate_ids = [c["id"] for c in candidates]
    products = _ordered_products(session, candidate_ids)
    return templates.TemplateResponse(
        request,
        "recommendations/generating.html",
        {
            "user": user,
            "products": products,
            "candidate_ids": ",".join(str(pid) for pid in candidate_ids),
            "trigger_reason": trigger_reason,
        },
    )


@router.get("", response_class=HTMLResponse)
def view_recommendations(
    request: Request,
    error: str | None = None,
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
) -> HTMLResponse:
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

        # First visit with real behavior to draw on - always generates,
        # regardless of the event-count trigger below (there's nothing
        # cached yet to prefer over).
        rendered = _render_generating(request, session, user, trigger_reason="manual")
        if rendered is not None:
            return rendered
        # Retrieval found no candidates at all (e.g. empty catalog) - store
        # the no-activity narrative so this doesn't re-attempt on every
        # visit.
        recommendation = _store_recommendation(session, user, NO_ACTIVITY_NARRATIVE, [])

    elif should_auto_regenerate(session, user, recommendation):
        # Enough new activity has landed since the cached recommendation
        # to make regenerating worthwhile (FR "Efficiency" - see
        # agent/triggers.py). Same streaming UX as first-generation.
        try:
            rendered = _render_generating(
                request, session, user, trigger_reason="threshold"
            )
        except Exception:
            # A Mesh/Qdrant failure here has a safe fallback available
            # (unlike the first-generation branch above) - the still-valid
            # cached recommendation below, so degrade to that instead of a
            # raw 500.
            logger.exception(
                "Auto-regeneration retrieval failed for user_id=%s", user.id
            )
            rendered = None
        if rendered is not None:
            return rendered
        # Retrieval came back empty (e.g. an emptied catalog) or failed -
        # fall back to serving the still-valid cached recommendation below
        # instead of showing nothing.

    ordered_products = _ordered_products(session, recommendation.product_ids)
    return templates.TemplateResponse(
        request,
        "recommendations/view.html",
        {
            "user": user,
            "recommendation": recommendation,
            "products": ordered_products,
            "error": REFRESH_ERROR_MESSAGES.get(error) if error else None,
        },
    )


@router.get("/stream")
def stream_narrative(
    candidate_ids: str,
    reason: str = "manual",
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """Server-Sent Events: streams the narrative for the product IDs already
    retrieved and shown by the initial page load (see view_recommendations
    above), then persists the finished Recommendation. Re-derives the
    profile (cheap, no Mesh call) but does not re-embed/re-retrieve - that
    already happened once, in the request that rendered generating.html.
    `reason` just carries through the trigger_reason ("manual" for a first
    generation, "threshold" for the auto-regenerate trigger) for
    observability - it doesn't change what's generated."""
    trigger_reason = reason if reason in ("manual", "threshold") else "manual"
    product_ids = [int(pid) for pid in candidate_ids.split(",") if pid]
    products = _ordered_products(session, product_ids)
    candidates = [
        {"id": p.id, "title": p.title, "category": p.category} for p in products
    ]

    def event_stream() -> Iterator[str]:
        if not candidates:
            yield "event: done\ndata: \n\n"
            return

        profile = build_profile(session, user)
        chunks: list[str] = []
        try:
            for chunk in generate_narrative_stream(profile, candidates):
                chunks.append(chunk)
                yield "data: " + chunk.replace("\n", "\ndata: ") + "\n\n"
        except Exception:
            logger.exception("Narrative streaming failed for user_id=%s", user.id)
            if not chunks:
                # A custom event named "error" would collide with
                # EventSource's own built-in connection-error handling
                # (inconsistent across browsers) - "failed" keeps the two
                # unambiguous on the client.
                yield "event: failed\ndata: \n\n"
                return
            # Real content already streamed to the client before the
            # failure - still worth persisting rather than losing it and
            # leaving the user stuck re-generating from scratch.

        narrative = "".join(chunks)
        _store_recommendation(session, user, narrative, product_ids, trigger_reason)
        yield "event: done\ndata: \n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/refresh")
def refresh_recommendations(
    category: str | None = None,
    max_price: float | None = None,
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """`category`/`max_price` are optional, narrowing retrieval to matching
    products (Phase 6 bonus: metadata filtering) - omitted, refresh behaves
    exactly as before."""
    try:
        narrative, product_ids = generate_recommendation(
            session, user, category=category, max_price=max_price
        )
    except Exception:
        # A Mesh/Qdrant failure here shouldn't surface as a raw 500 - the
        # user already has a valid cached recommendation to fall back to
        # (this route only reachable from the "Refresh" button on view.html,
        # which only renders once one exists).
        logger.exception("Recommendation refresh failed for user_id=%s", user.id)
        return RedirectResponse(
            url="/recommendations?error=refresh_failed",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    _store_recommendation(session, user, narrative, product_ids)
    return RedirectResponse(
        url="/recommendations", status_code=status.HTTP_303_SEE_OTHER
    )

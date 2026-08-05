from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.models.product import Product
from app.models.user import User
from app.services.auth import require_login

router = APIRouter(prefix="/recommendations")
templates = Jinja2Templates(directory="app/templates")

STARTING_POINTS_LIMIT = 3


@router.get("", response_class=HTMLResponse)
def view_recommendations(
    request: Request,
    user: User = Depends(require_login),
    session: Session = Depends(get_session),
):
    # No Recommendation model/agent yet (Phase 4) — every user is cold-start
    # today, so this route only ever renders the empty state for now.
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

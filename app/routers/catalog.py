from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.models.product import Product
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/catalog")
templates = Jinja2Templates(directory="app/templates")

PAGE_SIZE = 24


@router.get("", response_class=HTMLResponse)
def browse(
    request: Request,
    q: str = "",
    category: str = "",
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    statement = select(Product)
    if q:
        like = f"%{q}%"
        statement = statement.where(
            Product.title.ilike(like) | Product.description.ilike(like)
        )
    if category:
        statement = statement.where(Product.category == category)
    products = session.exec(statement.order_by(Product.title).limit(PAGE_SIZE)).all()

    categories = session.exec(
        select(Product.category).distinct().order_by(Product.category)
    ).all()

    return templates.TemplateResponse(
        request,
        "catalog/browse.html",
        {
            "user": user,
            "products": products,
            "categories": categories,
            "q": q,
            "selected_category": category,
        },
    )


@router.get("/{product_id}", response_class=HTMLResponse)
def detail(
    request: Request,
    product_id: int,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse(
        request, "catalog/detail.html", {"user": user, "product": product}
    )

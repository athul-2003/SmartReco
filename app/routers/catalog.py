from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from app.db import get_session
from app.models.product import Product
from app.models.user import User
from app.services.auth import get_current_user
from app.services.ui import category_cover

router = APIRouter(prefix="/catalog")
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["cover"] = category_cover

PAGE_SIZE = 24
RELATED_LIMIT = 3

SORT_OPTIONS = {
    "recommended": Product.title.asc(),
    "newest": Product.created_at.desc(),
    "price_asc": Product.price.asc(),
    "price_desc": Product.price.desc(),
}


def _page_numbers(page: int, total_pages: int) -> list[int | None]:
    """Truncated page list for pagination controls, e.g. [1, None, 4, 5, 6, None, 63]."""
    if total_pages <= 7:
        return list(range(1, total_pages + 1))
    keep = {1, total_pages, page - 1, page, page + 1}
    keep = sorted(p for p in keep if 1 <= p <= total_pages)
    result: list[int | None] = []
    previous = None
    for p in keep:
        if previous is not None and p - previous > 1:
            result.append(None)
        result.append(p)
        previous = p
    return result


def _filtered_statement(q: str, category: str):
    statement = select(Product)
    if q:
        like = f"%{q}%"
        statement = statement.where(
            Product.title.ilike(like) | Product.description.ilike(like)
        )
    if category:
        statement = statement.where(Product.category == category)
    return statement


@router.get("", response_class=HTMLResponse)
def browse(
    request: Request,
    q: str = "",
    category: str = "",
    sort: str = "recommended",
    page: int = 1,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    sort = sort if sort in SORT_OPTIONS else "recommended"
    base_statement = _filtered_statement(q, category)

    total_count = session.exec(
        select(func.count()).select_from(base_statement.subquery())
    ).one()
    total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(max(page, 1), total_pages)

    products = session.exec(
        base_statement.order_by(SORT_OPTIONS[sort])
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()

    categories = session.exec(
        select(Product.category, func.count(Product.id))
        .group_by(Product.category)
        .order_by(Product.category)
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
            "sort": sort,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "page_size": PAGE_SIZE,
            "page_numbers": _page_numbers(page, total_pages),
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

    related = session.exec(
        select(Product)
        .where(Product.category == product.category, Product.id != product.id)
        .order_by(Product.title)
        .limit(RELATED_LIMIT)
    ).all()

    return templates.TemplateResponse(
        request,
        "catalog/detail.html",
        {"user": user, "product": product, "related": related},
    )

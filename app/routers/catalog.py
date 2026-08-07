from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from app.db import get_session
from app.models.product import Product
from app.models.user import User
from app.services.auth import get_current_user
from app.services.products_query import filtered_statement, page_numbers
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


@router.get("", response_class=HTMLResponse)
def browse(
    request: Request,
    q: str = "",
    category: str = "",
    sort: str = "recommended",
    page: int = 1,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    sort = sort if sort in SORT_OPTIONS else "recommended"
    base_statement = filtered_statement(q, category)

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
            "page_numbers": page_numbers(page, total_pages),
        },
    )


@router.get("/{product_id}", response_class=HTMLResponse)
def detail(
    request: Request,
    product_id: int,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

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

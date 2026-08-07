from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from app.db import get_session
from app.models.product import Product
from app.models.user import User
from app.services import catalog
from app.services.auth import require_admin
from app.services.products_query import filtered_statement, page_numbers
from app.services.ui import category_cover

router = APIRouter(prefix="/admin/products")
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["cover"] = category_cover

PAGE_SIZE = 24


@router.get("", response_class=HTMLResponse)
def list_products(
    request: Request,
    q: str = "",
    category: str = "",
    page: int = 1,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    base_statement = filtered_statement(q, category)

    total_count = session.exec(
        select(func.count()).select_from(base_statement.subquery())
    ).one()
    total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(max(page, 1), total_pages)

    products = session.exec(
        base_statement.order_by(Product.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()

    categories = session.exec(
        select(Product.category).distinct().order_by(Product.category)
    ).all()

    return templates.TemplateResponse(
        request,
        "admin/products_list.html",
        {
            "user": user,
            "products": products,
            "categories": categories,
            "q": q,
            "selected_category": category,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "page_size": PAGE_SIZE,
            "page_numbers": page_numbers(page, total_pages),
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_product_form(
    request: Request, user: User = Depends(require_admin)
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "admin/product_form.html",
        {"user": user, "product": None, "mode": "create"},
    )


@router.post("/new")
def create_product(
    request: Request,
    title: str = Form(),
    description: str = Form(),
    category: str = Form(),
    price: float = Form(0.0),
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> Response:
    try:
        catalog.create_product(
            session,
            title=title,
            description=description,
            category=category,
            price=price,
        )
    except catalog.DualWriteError as exc:
        return templates.TemplateResponse(
            request,
            "admin/product_form.html",
            {
                "user": user,
                "product": {
                    "title": title,
                    "description": description,
                    "category": category,
                    "price": price,
                },
                "mode": "create",
                "error": str(exc),
            },
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    return RedirectResponse(
        url="/admin/products", status_code=status.HTTP_303_SEE_OTHER
    )


def _get_product_or_404(session: Session, product_id: int) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


@router.get("/{product_id}/edit", response_class=HTMLResponse)
def edit_product_form(
    request: Request,
    product_id: int,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    product = _get_product_or_404(session, product_id)
    return templates.TemplateResponse(
        request,
        "admin/product_form.html",
        {"user": user, "product": product, "mode": "edit"},
    )


@router.post("/{product_id}/edit")
def update_product(
    request: Request,
    product_id: int,
    title: str = Form(),
    description: str = Form(),
    category: str = Form(),
    price: float = Form(0.0),
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> Response:
    product = _get_product_or_404(session, product_id)
    try:
        catalog.update_product(
            session,
            product,
            title=title,
            description=description,
            category=category,
            price=price,
        )
    except catalog.DualWriteError as exc:
        return templates.TemplateResponse(
            request,
            "admin/product_form.html",
            {
                "user": user,
                "product": {
                    "id": product_id,
                    "title": title,
                    "description": description,
                    "category": category,
                    "price": price,
                },
                "mode": "edit",
                "error": str(exc),
            },
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    return RedirectResponse(
        url="/admin/products", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{product_id}/delete")
def delete_product(
    product_id: int,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    product = _get_product_or_404(session, product_id)
    try:
        catalog.delete_product(session, product)
    except catalog.DualWriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return RedirectResponse(
        url="/admin/products", status_code=status.HTTP_303_SEE_OTHER
    )

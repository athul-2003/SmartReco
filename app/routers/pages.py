from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from app.db import get_session
from app.models.product import Product
from app.models.user import Role, User
from app.services.auth import get_current_user, require_admin

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: User | None = Depends(get_current_user)) -> Response:
    if user is not None:
        return RedirectResponse(url="/catalog", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "home.html", {"user": user})


@router.get("/admin", response_class=HTMLResponse)
def admin_area(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    product_count = session.exec(select(func.count()).select_from(Product)).one()
    category_count = session.exec(
        select(func.count(func.distinct(Product.category)))
    ).one()
    user_count = session.exec(select(func.count()).select_from(User)).one()
    admin_count = session.exec(
        select(func.count()).select_from(User).where(User.role == Role.admin)
    ).one()
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "user": user,
            "product_count": product_count,
            "category_count": category_count,
            "user_count": user_count,
            "admin_count": admin_count,
        },
    )

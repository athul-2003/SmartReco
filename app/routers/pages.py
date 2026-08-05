from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models.user import User
from app.services.auth import get_current_user, require_admin

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: User | None = Depends(get_current_user)):
    if user is not None:
        return RedirectResponse(url="/catalog", status_code=303)
    return templates.TemplateResponse(request, "home.html", {"user": user})


@router.get("/admin", response_class=HTMLResponse)
def admin_area(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin.html", {"user": user})

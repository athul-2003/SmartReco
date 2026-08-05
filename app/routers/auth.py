from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.models.user import User
from app.services.auth import get_current_user, hash_password, verify_password

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request, user: User | None = Depends(get_current_user)):
    return templates.TemplateResponse(request, "register.html", {"user": user})


@router.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing is not None:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": "An account with that email already exists.", "user": None},
            status_code=400,
        )

    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)

    request.session["user_id"] = user.id
    return RedirectResponse(url="/catalog", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, user: User | None = Depends(get_current_user)):
    return templates.TemplateResponse(request, "login.html", {"user": user})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Incorrect email or password.", "user": None},
            status_code=400,
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/catalog", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

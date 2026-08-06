from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.models.user import User
from app.services.auth import (
    get_current_user,
    hash_password,
    safe_next_path,
    verify_password,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/register", response_class=HTMLResponse)
def register_form(
    request: Request,
    next: str | None = None,
    user: User | None = Depends(get_current_user),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "register.html", {"user": user, "next": next}
    )


@router.post("/register")
def register(
    request: Request,
    email: str = Form(),
    password: str = Form(),
    next: str | None = Form(None),
    session: Session = Depends(get_session),
) -> Response:
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing is not None:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "error": "An account with that email already exists.",
                "user": None,
                "next": next,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)

    request.session["user_id"] = user.id
    return RedirectResponse(
        url=safe_next_path(next), status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/login", response_class=HTMLResponse)
def login_form(
    request: Request,
    next: str | None = None,
    user: User | None = Depends(get_current_user),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "login.html", {"user": user, "next": next}
    )


@router.post("/login")
def login(
    request: Request,
    email: str = Form(),
    password: str = Form(),
    next: str | None = Form(None),
    session: Session = Depends(get_session),
) -> Response:
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Incorrect email or password.", "user": None, "next": next},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    request.session["user_id"] = user.id
    return RedirectResponse(
        url=safe_next_path(next), status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

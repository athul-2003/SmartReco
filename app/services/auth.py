from urllib.parse import quote

from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlmodel import Session

from app.db import get_session
from app.models.user import Role, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> User | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return session.get(User, user_id)


def safe_next_path(next: str | None, default: str = "/catalog") -> str:
    """Only ever redirect to a same-site relative path - a `next` value like
    `//evil.com` or `https://evil.com` would otherwise make login/register
    an open redirect. Falls back to `default` (the normal post-login
    landing page - `/catalog` for a regular user, `/admin` for an admin,
    decided by the caller) for anything else, including a missing value."""
    if next and next.startswith("/") and not next.startswith("//"):
        return next
    return default


def require_login(
    request: Request, user: User | None = Depends(get_current_user)
) -> User:
    if user is None:
        next_param = quote(request.url.path, safe="")
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/login?next={next_param}"},
        )
    return user


def require_admin(user: User = Depends(require_login)) -> User:
    if user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user

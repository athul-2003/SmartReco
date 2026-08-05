from datetime import UTC, datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class Role(str, Enum):
    user = "user"
    admin = "admin"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    role: Role = Field(default=Role.user)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

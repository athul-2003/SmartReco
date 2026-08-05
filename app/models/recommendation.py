from datetime import UTC, datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Recommendation(SQLModel, table=True):
    __tablename__ = "recommendations"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    narrative: str
    product_ids: list[int] = Field(sa_column=Column(JSON))
    trigger_reason: str = "manual"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)

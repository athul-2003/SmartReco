from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class EventType(str, Enum):
    view = "view"
    search = "search"
    click = "click"
    dwell = "dwell"


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    event_type: EventType
    product_id: int | None = Field(default=None, foreign_key="products.id", index=True)
    # Named `event_metadata`, not `metadata` - the latter is reserved on
    # SQLAlchemy declarative models (Base.metadata is the schema registry).
    event_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)

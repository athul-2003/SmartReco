from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db import get_session
from app.models.event import Event, EventType
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter()

MAX_BATCH_SIZE = 50


class EventIn(BaseModel):
    event_type: EventType
    product_id: int | None = None
    metadata: dict | None = None


class EventBatchIn(BaseModel):
    events: list[EventIn] = Field(min_length=1, max_length=MAX_BATCH_SIZE)


@router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
def ingest_events(
    batch: EventBatchIn,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    # A plain 401, not require_login's redirect-to-/login - this is a JSON
    # API hit by fetch()/sendBeacon, not a page navigation.
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    rows = [
        Event(
            user_id=user.id,
            event_type=e.event_type,
            product_id=e.product_id,
            event_metadata=e.metadata,
        )
        for e in batch.events
    ]
    session.add_all(rows)
    session.commit()

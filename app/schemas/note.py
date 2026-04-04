import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NoteCreate(BaseModel):
    title: str
    content: str = ""
    is_pinned: bool = False


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    is_pinned: bool | None = None


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


class NoteList(BaseModel):
    notes: list[NoteResponse]
    count: int

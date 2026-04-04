import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.schemas.note import NoteCreate, NoteUpdate


async def create_note(db: AsyncSession, payload: NoteCreate) -> Note:
    note = Note(**payload.model_dump())
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def get_notes(db: AsyncSession, search: str | None = None) -> list[Note]:
    stmt = select(Note).order_by(Note.created_at.desc())
    if search:
        stmt = stmt.where(Note.title.icontains(search))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_note(db: AsyncSession, note_id: uuid.UUID) -> Note | None:
    return await db.get(Note, note_id)


async def update_note(db: AsyncSession, note: Note, payload: NoteUpdate) -> Note:
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


async def delete_note(db: AsyncSession, note: Note) -> None:
    await db.delete(note)
    await db.commit()

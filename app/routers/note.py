import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.note import NoteCreate, NoteList, NoteResponse, NoteUpdate
from app.services import note as note_service

router = APIRouter(prefix="/api/v1/notes", tags=["notes"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(payload: NoteCreate, db: DbDep) -> NoteResponse:
    note = await note_service.create_note(db, payload)
    return NoteResponse.model_validate(note)


@router.get("/", response_model=NoteList)
async def list_notes(
    db: DbDep,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> NoteList:
    notes = await note_service.get_notes(db, search)
    return NoteList(
        notes=[NoteResponse.model_validate(n) for n in notes],
        count=len(notes),
    )


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: uuid.UUID, db: DbDep) -> NoteResponse:
    note = await note_service.get_note(db, note_id)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )
    return NoteResponse.model_validate(note)


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: uuid.UUID, payload: NoteUpdate, db: DbDep
) -> NoteResponse:
    note = await note_service.get_note(db, note_id)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )
    updated = await note_service.update_note(db, note, payload)
    return NoteResponse.model_validate(updated)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: uuid.UUID, db: DbDep) -> None:
    note = await note_service.get_note(db, note_id)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )
    await note_service.delete_note(db, note)

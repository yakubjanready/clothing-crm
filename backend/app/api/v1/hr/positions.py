from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.department import Department
from app.models.position import Position
from app.models.user import User
from app.schemas.position import PositionCreate, PositionRead, PositionUpdate
from app.services.audit import diff_attrs, log_activity
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/positions")
ENTITY = "position"


def _base_select(include_deleted: bool = False):
    stmt = select(Position).order_by(Position.name)
    if not include_deleted:
        stmt = stmt.where(Position.deleted_at.is_(None))
    return stmt


@router.get("", response_model=Page[PositionRead])
async def list_positions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("hr:read")),
    params: PageParams = Depends(page_params),
    search: str | None = Query(default=None, max_length=128),
    department_id: uuid.UUID | None = Query(default=None),
    include_deleted: bool = Query(default=False),
) -> Page[PositionRead]:
    stmt = _base_select(include_deleted=include_deleted)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Position.name.ilike(like), Position.code.ilike(like)))
    if department_id is not None:
        stmt = stmt.where(Position.department_id == department_id)

    items, total, pages = await paginate(db, stmt, params)
    return Page[PositionRead](
        items=[PositionRead.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.get("/{position_id}", response_model=PositionRead)
async def get_position(
    position_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("hr:read")),
) -> PositionRead:
    pos = await db.get(Position, position_id)
    if pos is None or pos.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lavozim topilmadi")
    return PositionRead.model_validate(pos)


@router.post("", response_model=PositionRead, status_code=status.HTTP_201_CREATED)
async def create_position(
    body: PositionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("hr:write")),
) -> PositionRead:
    if body.department_id is not None:
        dept = await db.get(Department, body.department_id)
        if dept is None or dept.deleted_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "department_id topilmadi")

    pos = Position(**body.model_dump())
    db.add(pos)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Code unique bo'lishi kerak") from e

    await log_activity(
        db,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type=ENTITY,
        entity_id=pos.id,
        changes=body.model_dump(),
        request=request,
    )
    await db.commit()
    await db.refresh(pos)
    return PositionRead.model_validate(pos)


@router.patch("/{position_id}", response_model=PositionRead)
async def update_position(
    position_id: uuid.UUID,
    body: PositionUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("hr:write")),
) -> PositionRead:
    pos = await db.get(Position, position_id)
    if pos is None or pos.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lavozim topilmadi")

    patch = body.model_dump(exclude_unset=True)
    allowed = {"name", "code", "description", "base_salary", "department_id"}
    changes = diff_attrs(pos, patch, allowed)
    for field, val in patch.items():
        if field in allowed:
            setattr(pos, field, val)

    if changes:
        await log_activity(
            db,
            actor=actor,
            action=AuditAction.UPDATE,
            entity_type=ENTITY,
            entity_id=pos.id,
            changes=changes,
            request=request,
        )
    await db.commit()
    await db.refresh(pos)
    return PositionRead.model_validate(pos)


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_position(
    position_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("hr:delete")),
) -> None:
    pos = await db.get(Position, position_id)
    if pos is None or pos.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lavozim topilmadi")

    pos.soft_delete()
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY,
        entity_id=pos.id,
        request=request,
    )
    await db.commit()


@router.post("/{position_id}/restore", response_model=PositionRead)
async def restore_position(
    position_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("hr:write")),
) -> PositionRead:
    pos = await db.get(Position, position_id)
    if pos is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lavozim topilmadi")
    if pos.deleted_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Lavozim o'chirilmagan")

    pos.restore()
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.RESTORE,
        entity_type=ENTITY,
        entity_id=pos.id,
        request=request,
    )
    await db.commit()
    await db.refresh(pos)
    return PositionRead.model_validate(pos)

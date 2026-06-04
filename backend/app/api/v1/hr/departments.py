from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.department import Department
from app.models.user import User
from app.schemas.department import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
)
from app.services.audit import diff_attrs, log_activity
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/departments")
ENTITY = "department"


def _base_select(include_deleted: bool = False):
    stmt = select(Department).order_by(Department.name)
    if not include_deleted:
        stmt = stmt.where(Department.deleted_at.is_(None))
    return stmt


@router.get("", response_model=Page[DepartmentRead])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("hr:read")),
    params: PageParams = Depends(page_params),
    search: str | None = Query(default=None, max_length=128),
    parent_id: uuid.UUID | None = Query(default=None),
    include_deleted: bool = Query(default=False),
) -> Page[DepartmentRead]:
    stmt = _base_select(include_deleted=include_deleted)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Department.name.ilike(like), Department.code.ilike(like)))
    if parent_id is not None:
        stmt = stmt.where(Department.parent_id == parent_id)

    items, total, pages = await paginate(db, stmt, params)
    return Page[DepartmentRead](
        items=[DepartmentRead.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.get("/{department_id}", response_model=DepartmentRead)
async def get_department(
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("hr:read")),
) -> DepartmentRead:
    dept = await db.get(Department, department_id)
    if dept is None or dept.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bo'lim topilmadi")
    return DepartmentRead.model_validate(dept)


@router.post("", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
async def create_department(
    body: DepartmentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("hr:write")),
) -> DepartmentRead:
    if body.parent_id is not None:
        parent = await db.get(Department, body.parent_id)
        if parent is None or parent.deleted_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "parent_id topilmadi")

    dept = Department(**body.model_dump())
    db.add(dept)
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
        entity_id=dept.id,
        changes=body.model_dump(),
        request=request,
    )
    await db.commit()
    await db.refresh(dept)
    return DepartmentRead.model_validate(dept)


@router.patch("/{department_id}", response_model=DepartmentRead)
async def update_department(
    department_id: uuid.UUID,
    body: DepartmentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("hr:write")),
) -> DepartmentRead:
    dept = await db.get(Department, department_id)
    if dept is None or dept.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bo'lim topilmadi")

    patch = body.model_dump(exclude_unset=True)
    if "parent_id" in patch and patch["parent_id"] is not None:
        if patch["parent_id"] == department_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "parent_id == id bo'la olmaydi")
        parent = await db.get(Department, patch["parent_id"])
        if parent is None or parent.deleted_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "parent_id topilmadi")

    allowed = {"name", "code", "description", "parent_id"}
    changes = diff_attrs(dept, patch, allowed)
    for field, val in patch.items():
        if field in allowed:
            setattr(dept, field, val)

    if changes:
        await log_activity(
            db,
            actor=actor,
            action=AuditAction.UPDATE,
            entity_type=ENTITY,
            entity_id=dept.id,
            changes=changes,
            request=request,
        )
    await db.commit()
    await db.refresh(dept)
    return DepartmentRead.model_validate(dept)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_department(
    department_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("hr:delete")),
) -> None:
    dept = await db.get(Department, department_id)
    if dept is None or dept.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bo'lim topilmadi")

    dept.soft_delete()
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY,
        entity_id=dept.id,
        request=request,
    )
    await db.commit()


@router.post("/{department_id}/restore", response_model=DepartmentRead)
async def restore_department(
    department_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("hr:write")),
) -> DepartmentRead:
    dept = await db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bo'lim topilmadi")
    if dept.deleted_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bo'lim o'chirilmagan")

    dept.restore()
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.RESTORE,
        entity_type=ENTITY,
        entity_id=dept.id,
        request=request,
    )
    await db.commit()
    await db.refresh(dept)
    return DepartmentRead.model_validate(dept)

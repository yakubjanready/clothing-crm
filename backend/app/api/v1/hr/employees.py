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
from app.models.employee import Employee, EmployeeStatus
from app.models.position import Position
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.services.audit import diff_attrs, log_activity
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/employees")
ENTITY = "employee"


def _base_select(include_deleted: bool = False):
    stmt = select(Employee).order_by(Employee.last_name, Employee.first_name)
    if not include_deleted:
        stmt = stmt.where(Employee.deleted_at.is_(None))
    return stmt


async def _ensure_refs(db: AsyncSession, dept_id, pos_id) -> None:
    if dept_id is not None:
        dept = await db.get(Department, dept_id)
        if dept is None or dept.deleted_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "department_id topilmadi")
    if pos_id is not None:
        pos = await db.get(Position, pos_id)
        if pos is None or pos.deleted_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "position_id topilmadi")


@router.get("", response_model=Page[EmployeeRead])
async def list_employees(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("hr:read")),
    params: PageParams = Depends(page_params),
    search: str | None = Query(default=None, max_length=128),
    department_id: uuid.UUID | None = Query(default=None),
    position_id: uuid.UUID | None = Query(default=None),
    status_: EmployeeStatus | None = Query(default=None, alias="status"),
    include_deleted: bool = Query(default=False),
) -> Page[EmployeeRead]:
    stmt = _base_select(include_deleted=include_deleted)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Employee.first_name.ilike(like),
                Employee.last_name.ilike(like),
                Employee.email.ilike(like),
            )
        )
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    if position_id is not None:
        stmt = stmt.where(Employee.position_id == position_id)
    if status_ is not None:
        stmt = stmt.where(Employee.status == status_)

    items, total, pages = await paginate(db, stmt, params)
    return Page[EmployeeRead](
        items=[EmployeeRead.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("hr:read")),
) -> EmployeeRead:
    emp = await db.get(Employee, employee_id)
    if emp is None or emp.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Xodim topilmadi")
    return EmployeeRead.model_validate(emp)


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def create_employee(
    body: EmployeeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("hr:write")),
) -> EmployeeRead:
    await _ensure_refs(db, body.department_id, body.position_id)

    emp = Employee(**body.model_dump())
    db.add(emp)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email yoki user_id band") from e

    await log_activity(
        db,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type=ENTITY,
        entity_id=emp.id,
        changes=body.model_dump(),
        request=request,
    )
    await db.commit()
    await db.refresh(emp)
    return EmployeeRead.model_validate(emp)


@router.patch("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: uuid.UUID,
    body: EmployeeUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("hr:write")),
) -> EmployeeRead:
    emp = await db.get(Employee, employee_id)
    if emp is None or emp.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Xodim topilmadi")

    patch = body.model_dump(exclude_unset=True)
    await _ensure_refs(
        db,
        patch.get("department_id") if "department_id" in patch else None,
        patch.get("position_id") if "position_id" in patch else None,
    )

    allowed = {
        "first_name", "last_name", "email", "phone", "photo_url",
        "status", "hire_date", "termination_date",
        "department_id", "position_id", "user_id",
    }
    changes = diff_attrs(emp, patch, allowed)
    for field, val in patch.items():
        if field in allowed:
            setattr(emp, field, val)

    if changes:
        await log_activity(
            db,
            actor=actor,
            action=AuditAction.UPDATE,
            entity_type=ENTITY,
            entity_id=emp.id,
            changes=changes,
            request=request,
        )
    await db.commit()
    await db.refresh(emp)
    return EmployeeRead.model_validate(emp)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_employee(
    employee_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("hr:delete")),
) -> None:
    emp = await db.get(Employee, employee_id)
    if emp is None or emp.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Xodim topilmadi")

    emp.soft_delete()
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY,
        entity_id=emp.id,
        request=request,
    )
    await db.commit()


@router.post("/{employee_id}/restore", response_model=EmployeeRead)
async def restore_employee(
    employee_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("hr:write")),
) -> EmployeeRead:
    emp = await db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Xodim topilmadi")
    if emp.deleted_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Xodim o'chirilmagan")

    emp.restore()
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.RESTORE,
        entity_type=ENTITY,
        entity_id=emp.id,
        request=request,
    )
    await db.commit()
    await db.refresh(emp)
    return EmployeeRead.model_validate(emp)

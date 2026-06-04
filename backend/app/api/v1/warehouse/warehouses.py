from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.user import User
from app.models.warehouse import Warehouse, WarehouseType
from app.schemas.warehouse import WarehouseCreate, WarehouseRead, WarehouseUpdate
from app.services.audit import diff_attrs, log_activity
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/warehouses")
ENTITY = "warehouse"


def _base(include_deleted: bool):
    stmt = select(Warehouse).order_by(Warehouse.name)
    if not include_deleted:
        stmt = stmt.where(Warehouse.deleted_at.is_(None))
    return stmt


@router.get("", response_model=Page[WarehouseRead])
async def list_warehouses(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("warehouse:read")),
    params: PageParams = Depends(page_params),
    search: str | None = Query(default=None, max_length=128),
    type_: WarehouseType | None = Query(default=None, alias="type"),
    is_active: bool | None = Query(default=None),
    include_deleted: bool = Query(default=False),
) -> Page[WarehouseRead]:
    stmt = _base(include_deleted)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Warehouse.name.ilike(like), Warehouse.code.ilike(like)))
    if type_ is not None:
        stmt = stmt.where(Warehouse.type == type_)
    if is_active is not None:
        stmt = stmt.where(Warehouse.is_active == is_active)

    items, total, pages = await paginate(db, stmt, params)
    return Page[WarehouseRead](
        items=[WarehouseRead.model_validate(i) for i in items],
        total=total, page=params.page, page_size=params.page_size, pages=pages,
    )


@router.get("/{warehouse_id}", response_model=WarehouseRead)
async def get_warehouse(
    warehouse_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("warehouse:read")),
) -> WarehouseRead:
    w = await db.get(Warehouse, warehouse_id)
    if w is None or w.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ombor topilmadi")
    return WarehouseRead.model_validate(w)


@router.post("", response_model=WarehouseRead, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    body: WarehouseCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("warehouse:write")),
) -> WarehouseRead:
    w = Warehouse(**body.model_dump())
    db.add(w)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "code band") from e

    await log_activity(
        db, actor=actor, action=AuditAction.CREATE,
        entity_type=ENTITY, entity_id=w.id, changes=body.model_dump(), request=request,
    )
    await db.commit()
    await db.refresh(w)
    return WarehouseRead.model_validate(w)


@router.patch("/{warehouse_id}", response_model=WarehouseRead)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    body: WarehouseUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("warehouse:write")),
) -> WarehouseRead:
    w = await db.get(Warehouse, warehouse_id)
    if w is None or w.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ombor topilmadi")

    patch = body.model_dump(exclude_unset=True)
    allowed = {"name", "code", "type", "address", "is_active", "manager_id"}
    changes = diff_attrs(w, patch, allowed)
    for f, v in patch.items():
        if f in allowed:
            setattr(w, f, v)

    if changes:
        await log_activity(
            db, actor=actor, action=AuditAction.UPDATE,
            entity_type=ENTITY, entity_id=w.id, changes=changes, request=request,
        )
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "code band") from e
    await db.refresh(w)
    return WarehouseRead.model_validate(w)


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_warehouse(
    warehouse_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("warehouse:write")),
) -> None:
    w = await db.get(Warehouse, warehouse_id)
    if w is None or w.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ombor topilmadi")
    w.soft_delete()
    await log_activity(
        db, actor=actor, action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY, entity_id=w.id, request=request,
    )
    await db.commit()


@router.post("/{warehouse_id}/restore", response_model=WarehouseRead)
async def restore_warehouse(
    warehouse_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("warehouse:write")),
) -> WarehouseRead:
    w = await db.get(Warehouse, warehouse_id)
    if w is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ombor topilmadi")
    if w.deleted_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ombor o'chirilmagan")
    w.restore()
    await log_activity(
        db, actor=actor, action=AuditAction.RESTORE,
        entity_type=ENTITY, entity_id=w.id, request=request,
    )
    await db.commit()
    await db.refresh(w)
    return WarehouseRead.model_validate(w)

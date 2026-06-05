from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.account import Account, AccountType
from app.models.activity_log import AuditAction
from app.models.user import User
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.services.audit import diff_attrs, log_activity
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/accounts")
ENTITY = "account"


def _base(include_deleted: bool):
    stmt = select(Account).order_by(Account.name)
    if not include_deleted:
        stmt = stmt.where(Account.deleted_at.is_(None))
    return stmt


@router.get("", response_model=Page[AccountRead])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("accounting:read")),
    params: PageParams = Depends(page_params),
    type_: AccountType | None = Query(default=None, alias="type"),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=128),
    include_deleted: bool = Query(default=False),
) -> Page[AccountRead]:
    stmt = _base(include_deleted)
    if type_ is not None:
        stmt = stmt.where(Account.type == type_)
    if is_active is not None:
        stmt = stmt.where(Account.is_active == is_active)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Account.name.ilike(like), Account.code.ilike(like)))

    items, total, pages = await paginate(db, stmt, params)
    return Page[AccountRead](
        items=[AccountRead.model_validate(i) for i in items],
        total=total, page=params.page, page_size=params.page_size, pages=pages,
    )


@router.get("/{account_id}", response_model=AccountRead)
async def get_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("accounting:read")),
) -> AccountRead:
    a = await db.get(Account, account_id)
    if a is None or a.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account topilmadi")
    return AccountRead.model_validate(a)


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: AccountCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("accounting:write")),
) -> AccountRead:
    data = body.model_dump(exclude={"initial_balance"})
    data["balance"] = body.initial_balance
    a = Account(**data)
    db.add(a)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "name yoki code band") from e

    await log_activity(
        db, actor=actor, action=AuditAction.CREATE,
        entity_type=ENTITY, entity_id=a.id, changes=body.model_dump(), request=request,
    )
    await db.commit()
    await db.refresh(a)
    return AccountRead.model_validate(a)


@router.patch("/{account_id}", response_model=AccountRead)
async def update_account(
    account_id: uuid.UUID,
    body: AccountUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("accounting:write")),
) -> AccountRead:
    a = await db.get(Account, account_id)
    if a is None or a.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account topilmadi")

    patch = body.model_dump(exclude_unset=True)
    allowed = {
        "name", "code", "type", "currency",
        "description", "bank_name", "account_number", "is_active",
    }
    changes = diff_attrs(a, patch, allowed)
    for f, v in patch.items():
        if f in allowed:
            setattr(a, f, v)

    if changes:
        await log_activity(
            db, actor=actor, action=AuditAction.UPDATE,
            entity_type=ENTITY, entity_id=a.id, changes=changes, request=request,
        )
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "name yoki code band") from e
    await db.refresh(a)
    return AccountRead.model_validate(a)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_account(
    account_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("accounting:write")),
) -> None:
    a = await db.get(Account, account_id)
    if a is None or a.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account topilmadi")
    if a.balance != 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Balans nol bo'lishi kerak (joriy: {a.balance})",
        )
    a.soft_delete()
    await log_activity(
        db, actor=actor, action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY, entity_id=a.id, request=request,
    )
    await db.commit()

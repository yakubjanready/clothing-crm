from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.debt_record import DebtDirection, DebtPartyType, DebtRecord
from app.models.user import User
from app.schemas.debt_record import DebtRecordRead
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/debts")


@router.get("", response_model=Page[DebtRecordRead])
async def list_debt_records(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("accounting:read")),
    params: PageParams = Depends(page_params),
    party_type: DebtPartyType | None = Query(default=None),
    party_id: uuid.UUID | None = Query(default=None),
    direction: DebtDirection | None = Query(default=None),
    reference_type: str | None = Query(default=None, max_length=64),
) -> Page[DebtRecordRead]:
    stmt = select(DebtRecord).order_by(DebtRecord.created_at.desc())
    if party_type is not None:
        stmt = stmt.where(DebtRecord.party_type == party_type)
    if party_id is not None:
        stmt = stmt.where(DebtRecord.party_id == party_id)
    if direction is not None:
        stmt = stmt.where(DebtRecord.direction == direction)
    if reference_type is not None:
        stmt = stmt.where(DebtRecord.reference_type == reference_type)

    items, total, pages = await paginate(db, stmt, params)
    return Page[DebtRecordRead](
        items=[DebtRecordRead.model_validate(i) for i in items],
        total=total, page=params.page, page_size=params.page_size, pages=pages,
    )

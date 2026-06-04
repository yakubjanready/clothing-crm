from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.schemas.activity_log import ActivityLogRead
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/audit-logs")


@router.get("", response_model=Page[ActivityLogRead])
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("audit:read")),
    params: PageParams = Depends(page_params),
    actor_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None, max_length=32),
    entity_type: str | None = Query(default=None, max_length=64),
    entity_id: uuid.UUID | None = Query(default=None),
) -> Page[ActivityLogRead]:
    stmt = select(ActivityLog).order_by(ActivityLog.created_at.desc())
    if actor_id is not None:
        stmt = stmt.where(ActivityLog.actor_id == actor_id)
    if action is not None:
        stmt = stmt.where(ActivityLog.action == action)
    if entity_type is not None:
        stmt = stmt.where(ActivityLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(ActivityLog.entity_id == entity_id)

    items, total, pages = await paginate(db, stmt, params)
    return Page[ActivityLogRead](
        items=[ActivityLogRead.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )

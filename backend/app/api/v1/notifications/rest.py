from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationRead,
    UnreadCount,
)
from app.services.audit import log_activity
from app.services.notify import notify
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/notifications")


def _user_scope(stmt, user_id: uuid.UUID):
    """User'niki yoki broadcast (user_id IS NULL)."""
    return stmt.where(or_(Notification.user_id == user_id, Notification.user_id.is_(None)))


@router.get("", response_model=Page[NotificationRead])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    params: PageParams = Depends(page_params),
    unread_only: bool = Query(default=False),
    type_: NotificationType | None = Query(default=None, alias="type"),
) -> Page[NotificationRead]:
    stmt = select(Notification).order_by(Notification.created_at.desc())
    stmt = _user_scope(stmt, user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    if type_ is not None:
        stmt = stmt.where(Notification.type == type_)

    items, total, pages = await paginate(db, stmt, params)
    return Page[NotificationRead](
        items=[NotificationRead.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UnreadCount:
    stmt = select(func.count(Notification.id)).where(Notification.read_at.is_(None))
    stmt = _user_scope(stmt, user.id)
    n = (await db.execute(stmt)).scalar_one()
    return UnreadCount(unread=n)


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationRead:
    n = await db.get(Notification, notification_id)
    if n is None or (n.user_id is not None and n.user_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notifikatsiya topilmadi")
    if n.read_at is None:
        n.read_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(n)
    return NotificationRead.model_validate(n)


@router.post("/mark-all-read", response_model=UnreadCount)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UnreadCount:
    now = datetime.now(UTC)
    await db.execute(
        update(Notification)
        .where(
            or_(Notification.user_id == user.id, Notification.user_id.is_(None)),
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
    )
    await db.commit()
    return UnreadCount(unread=0)


# Admin: qo'lda yaratish (test/eslatma maqsadi uchun)
@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
async def create_notification(
    body: NotificationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("user:write")),
) -> NotificationRead:
    n = await notify(
        db,
        type_=body.type,
        title=body.title,
        message=body.message,
        user_id=body.user_id,
        severity=body.severity,
        data=body.data,
    )
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="notification",
        entity_id=n.id,
        changes={"type": body.type, "title": body.title},
        request=request,
    )
    await db.commit()
    await db.refresh(n)
    return NotificationRead.model_validate(n)

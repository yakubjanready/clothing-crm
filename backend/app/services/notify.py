"""Markaziy notifikatsiya xizmati.

`notify()` 3 ta narsani amalga oshiradi:
  1. DB ga Notification yozadi (yumshoq audit + history)
  2. Redis Pub/Sub "notifications" kanaliga JSON publish qiladi
     (faol WebSocket connection'lar uni o'qiydi)
  3. Tanlangan outbound channellar (email/telegram) uchun Celery task yuboradi
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.notification import (
    Notification,
    NotificationSeverity,
    NotificationType,
)

REDIS_CHANNEL = "notifications"
logger = logging.getLogger(__name__)


async def notify(
    db: AsyncSession,
    *,
    type_: NotificationType,
    title: str,
    message: str,
    user_id: uuid.UUID | None = None,
    severity: NotificationSeverity = NotificationSeverity.INFO,
    data: dict[str, Any] | None = None,
    channels: tuple[str, ...] = ("websocket",),
) -> Notification:
    """Notifikatsiya yaratadi va tarqatadi. Caller `await db.commit()` qilishi kerak.

    Args:
        user_id: None bo'lsa — broadcast (barcha foydalanuvchilarga).
        channels: "websocket" (Redis publish), "email", "telegram".
                 "websocket" har doim shu funksiya orqali Redis'ga jo'natiladi.
    """
    notif = Notification(
        user_id=user_id,
        type=type_,
        severity=severity,
        title=title,
        message=message,
        data=jsonable_encoder(data) if data else None,
    )
    db.add(notif)
    await db.flush()

    # --- 1. Redis Pub/Sub ---
    payload = {
        "id": str(notif.id),
        "type": str(type_),
        "severity": str(severity),
        "title": title,
        "message": message,
        "data": notif.data,
        "user_id": str(user_id) if user_id else None,
        "created_at": notif.created_at.isoformat() if notif.created_at else None,
    }
    try:
        redis = get_redis()
        await redis.publish(REDIS_CHANNEL, json.dumps(payload, default=str))
    except Exception:  # noqa: BLE001 — broker yo'qligi flow'ni buzmasin
        logger.exception("notify: redis publish failed")

    # --- 2. Outbound channellar (Celery) ---
    if "email" in channels:
        try:
            from app.tasks.celery_app import celery_app
            celery_app.send_task(
                "send_email_notification", args=[str(notif.id)]
            )
            notif.sent_via_email = True
        except Exception:  # noqa: BLE001
            logger.exception("notify: email celery dispatch failed")

    if "telegram" in channels:
        try:
            from app.tasks.celery_app import celery_app
            celery_app.send_task(
                "send_telegram_notification", args=[str(notif.id)]
            )
            notif.sent_via_telegram = True
        except Exception:  # noqa: BLE001
            logger.exception("notify: telegram celery dispatch failed")

    await db.flush()
    return notif


__all__ = ["notify", "REDIS_CHANNEL"]

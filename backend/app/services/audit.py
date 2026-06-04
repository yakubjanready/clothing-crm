"""Audit yozish — har bir CRUD amalini ActivityLog'ga yozadi."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog, AuditAction
from app.models.user import User


def _client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


async def log_activity(
    db: AsyncSession,
    *,
    actor: User | None,
    action: AuditAction | str,
    entity_type: str,
    entity_id: uuid.UUID,
    changes: dict[str, Any] | None = None,
    request: Request | None = None,
) -> ActivityLog:
    log = ActivityLog(
        actor_id=actor.id if actor else None,
        action=str(action),
        entity_type=entity_type,
        entity_id=entity_id,
        changes=jsonable_encoder(changes) if changes else None,
        ip_address=_client_ip(request),
    )
    db.add(log)
    await db.flush()  # commit qilmaymiz — chaqiruvchi tranzaksiyani boshqaradi
    return log


def diff_attrs(
    obj: Any, patch: dict[str, Any], allowed: set[str]
) -> dict[str, dict[str, Any]]:
    """`obj`'ning hozirgi qiymatlari va `patch` ichidagi yangi qiymatlar farqi.
    Faqat `allowed` ichidagi maydonlar tekshiriladi.
    """
    changes: dict[str, dict[str, Any]] = {}
    for field, new_value in patch.items():
        if field not in allowed:
            continue
        old_value = getattr(obj, field, None)
        if old_value != new_value:
            changes[field] = {
                "old": jsonable_encoder(old_value),
                "new": jsonable_encoder(new_value),
            }
    return changes

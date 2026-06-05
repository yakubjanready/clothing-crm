"""WebSocket endpoint /ws/notifications — JWT auth + Redis Pub/Sub'dan tarqatish."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.security import InvalidTokenError, decode_token
from app.db.session import get_db
from app.models.user import User
from app.services.notify import REDIS_CHANNEL

router = APIRouter(prefix="/ws")
logger = logging.getLogger(__name__)


async def authenticate_ws_token(
    token: str, db: AsyncSession
) -> User | None:
    """JWT access tokendan User'ni topadi. Yaroqsiz/faol bo'lmagan → None."""
    try:
        payload = decode_token(token, expected_type="access")
        user_id = uuid.UUID(payload["sub"])
    except (InvalidTokenError, ValueError, KeyError):
        return None

    user = await db.get(User, user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        return None
    return user


@router.websocket("/notifications")
async def notifications_ws(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Live notifications stream. Redis Pub/Sub kanaliga subscribe va user'ga
    moslangan xabarlarni JSON formatda yuboradi.

    Faqat shu user'niki va broadcast (user_id IS NULL) xabarlar uzatiladi.
    """
    user = await authenticate_ws_token(token, db)
    if user is None:
        await websocket.close(code=1008, reason="Invalid token")
        return

    await websocket.accept()
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(REDIS_CHANNEL)
    user_id_str = str(user.id)

    try:
        # Listen loop — Redis Pub/Sub'dan kelgan xabarlarni WS ga yuboramiz
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                payload = json.loads(message["data"])
            except (TypeError, ValueError):
                continue

            target = payload.get("user_id")
            if target is None or target == user_id_str:
                await websocket.send_json(payload)
    except WebSocketDisconnect:
        logger.debug("ws disconnected user=%s", user_id_str)
    except Exception:  # noqa: BLE001
        logger.exception("ws error user=%s", user_id_str)
    finally:
        try:
            await pubsub.unsubscribe(REDIS_CHANNEL)
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            pass


# Backward compat & testing: /ws/health
@router.get("/health")
async def ws_health() -> dict[str, str]:
    return {"ws": "ready", "channel": REDIS_CHANNEL}

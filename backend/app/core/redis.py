"""Async Redis klienti — lazy singleton."""
from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import settings

_client: Redis | None = None


def get_redis() -> Redis:
    """FastAPI dependency va boshqa joylar uchun yagona Redis instansi."""
    global _client
    if _client is None:
        _client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


async def close_redis() -> None:
    """App shutdown'da chaqiriladi."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

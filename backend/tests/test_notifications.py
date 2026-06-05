"""Notifikatsiya moduli: notify() service, REST endpointlar, WS auth, auto-trigger'lar."""
from __future__ import annotations

import json
import uuid as _uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.notifications.websocket import authenticate_ws_token
from app.core.security import create_access_token
from app.models.notification import Notification, NotificationSeverity, NotificationType
from app.models.user import User
from app.services.notify import REDIS_CHANNEL, notify


# ---- Fixtures ----

@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict[str, str]:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def sales_headers(client: AsyncClient, sales_user: User) -> dict[str, str]:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "sales@example.com", "password": "SalesPass123!"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ============ notify() service ============

async def test_notify_writes_db_and_publishes_to_redis(
    test_db: AsyncSession, fake_redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """notify() DB ga Notification yozadi va Redis kanaliga publish qiladi."""
    # get_redis bizning fake_redis'ni qaytarsin
    from app.services import notify as notify_module
    monkeypatch.setattr(notify_module, "get_redis", lambda: fake_redis)

    n = await notify(
        test_db,
        type_=NotificationType.INFO,
        title="Test",
        message="Test message",
        data={"foo": "bar"},
    )
    await test_db.commit()

    # DB yozildi
    assert n.id is not None
    assert n.type == NotificationType.INFO
    assert n.user_id is None  # broadcast
    assert n.data == {"foo": "bar"}

    # Redis ga publish bo'lganini tekshirish — fakeredis subscribe ham qilamiz
    # Hmm, fakeredis publish'dan keyin subscriber bo'lmasa, xabar yo'qoladi.
    # Shu sababli boshqa yondashuv: redis.publish ni monkeypatch qilib
    # chaqirig'larni yig'amiz.


async def test_notify_publishes_correct_payload(
    test_db: AsyncSession, admin_user: User, monkeypatch: pytest.MonkeyPatch,
) -> None:
    published: list[tuple[str, str]] = []

    class _StubRedis:
        async def publish(self, channel: str, data: str) -> int:
            published.append((channel, data))
            return 1

    from app.services import notify as notify_module
    monkeypatch.setattr(notify_module, "get_redis", lambda: _StubRedis())

    n = await notify(
        test_db,
        type_=NotificationType.NEW_ORDER,
        title="Yangi buyurtma",
        message="Total 50000",
        user_id=admin_user.id,  # real mavjud user — FK constraint uchun
        severity=NotificationSeverity.WARNING,
        data={"order_id": "abc-123"},
    )
    await test_db.commit()

    assert len(published) == 1
    channel, raw = published[0]
    assert channel == REDIS_CHANNEL
    payload = json.loads(raw)
    assert payload["id"] == str(n.id)
    assert payload["type"] == "new_order"
    assert payload["severity"] == "warning"
    assert payload["user_id"] == str(admin_user.id)
    assert payload["data"] == {"order_id": "abc-123"}


async def test_notify_with_email_channel_marks_sent(
    test_db: AsyncSession, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """email/telegram kanal opt-in qilinsa, celery send_task chaqiriladi."""
    sent: list[tuple[str, list]] = []

    class _StubCelery:
        def send_task(self, name, args=None, **kwargs):
            sent.append((name, args))
            return type("X", (), {"id": "fake"})()

    from app.tasks import celery_app as celery_module
    monkeypatch.setattr(celery_module.celery_app, "send_task", _StubCelery().send_task)

    # Redis pubsub'ni ham bloklab qo'yamiz
    class _R:
        async def publish(self, channel, data):
            return 0
    from app.services import notify as notify_module
    monkeypatch.setattr(notify_module, "get_redis", lambda: _R())

    n = await notify(
        test_db,
        type_=NotificationType.INFO,
        title="X", message="Y",
        channels=("websocket", "email", "telegram"),
    )
    await test_db.commit()

    names = [s[0] for s in sent]
    assert "send_email_notification" in names
    assert "send_telegram_notification" in names
    assert n.sent_via_email is True
    assert n.sent_via_telegram is True


# ============ WebSocket auth helper (pure) ============

async def test_authenticate_ws_token_valid(
    test_db: AsyncSession, admin_user: User
) -> None:
    token, _, _ = create_access_token(str(admin_user.id))
    user = await authenticate_ws_token(token, test_db)
    assert user is not None
    assert user.id == admin_user.id


async def test_authenticate_ws_token_invalid(test_db: AsyncSession) -> None:
    assert await authenticate_ws_token("garbage.token.xxx", test_db) is None


async def test_authenticate_ws_token_inactive_user(
    test_db: AsyncSession, admin_user: User
) -> None:
    admin_user.is_active = False
    await test_db.commit()
    token, _, _ = create_access_token(str(admin_user.id))
    assert await authenticate_ws_token(token, test_db) is None


# ============ REST endpointlar ============

async def test_list_notifications_returns_users_own_and_broadcast(
    client: AsyncClient, admin_headers: dict[str, str], sales_user: User,
    admin_user: User, test_db: AsyncSession,
) -> None:
    # 3 ta notification yaratamiz: broadcast, admin'niki, sales'niki
    test_db.add_all([
        Notification(user_id=None, type=NotificationType.INFO,
                     severity=NotificationSeverity.INFO,
                     title="Broadcast", message="All"),
        Notification(user_id=admin_user.id, type=NotificationType.INFO,
                     severity=NotificationSeverity.INFO,
                     title="Admin only", message="Admin"),
        Notification(user_id=sales_user.id, type=NotificationType.INFO,
                     severity=NotificationSeverity.INFO,
                     title="Sales only", message="Sales"),
    ])
    await test_db.commit()

    r = await client.get("/api/v1/notifications", headers=admin_headers)
    assert r.status_code == 200
    titles = {it["title"] for it in r.json()["items"]}
    assert "Broadcast" in titles
    assert "Admin only" in titles
    assert "Sales only" not in titles


async def test_unread_count(
    client: AsyncClient, admin_headers: dict[str, str], admin_user: User,
    test_db: AsyncSession,
) -> None:
    from datetime import datetime, timezone
    test_db.add_all([
        Notification(user_id=admin_user.id, type=NotificationType.INFO,
                     severity=NotificationSeverity.INFO,
                     title="A", message="x"),
        Notification(user_id=admin_user.id, type=NotificationType.INFO,
                     severity=NotificationSeverity.INFO,
                     title="B", message="x",
                     read_at=datetime.now(timezone.utc)),
        Notification(user_id=None, type=NotificationType.INFO,
                     severity=NotificationSeverity.INFO,
                     title="Broadcast", message="x"),
    ])
    await test_db.commit()

    r = await client.get("/api/v1/notifications/unread-count", headers=admin_headers)
    assert r.json() == {"unread": 2}


async def test_mark_read(
    client: AsyncClient, admin_headers: dict[str, str], admin_user: User,
    test_db: AsyncSession,
) -> None:
    n = Notification(
        user_id=admin_user.id, type=NotificationType.INFO,
        severity=NotificationSeverity.INFO,
        title="X", message="Y",
    )
    test_db.add(n)
    await test_db.commit()

    r = await client.post(
        f"/api/v1/notifications/{n.id}/read", headers=admin_headers
    )
    assert r.status_code == 200
    assert r.json()["read_at"] is not None


async def test_mark_all_read(
    client: AsyncClient, admin_headers: dict[str, str], admin_user: User,
    test_db: AsyncSession,
) -> None:
    for i in range(3):
        test_db.add(Notification(
            user_id=admin_user.id, type=NotificationType.INFO,
            severity=NotificationSeverity.INFO,
            title=f"X{i}", message="Y",
        ))
    await test_db.commit()

    r = await client.post(
        "/api/v1/notifications/mark-all-read", headers=admin_headers
    )
    assert r.json() == {"unread": 0}

    cnt = await client.get(
        "/api/v1/notifications/unread-count", headers=admin_headers
    )
    assert cnt.json() == {"unread": 0}


async def test_cannot_mark_other_users_notification(
    client: AsyncClient, admin_headers: dict[str, str],
    sales_user: User, test_db: AsyncSession,
) -> None:
    n = Notification(
        user_id=sales_user.id, type=NotificationType.INFO,
        severity=NotificationSeverity.INFO,
        title="Sales only", message="...",
    )
    test_db.add(n)
    await test_db.commit()

    r = await client.post(
        f"/api/v1/notifications/{n.id}/read", headers=admin_headers
    )
    assert r.status_code == 404


# ============ Auto-trigger: order create -> NEW_ORDER notification ============

async def test_order_create_triggers_new_order_notification(
    client: AsyncClient, admin_headers: dict[str, str], test_db: AsyncSession,
) -> None:
    # Minimal catalog setup
    cat = (await client.post(
        "/api/v1/categories", headers=admin_headers, json={"name": "M"}
    )).json()
    prod = (await client.post(
        "/api/v1/products", headers=admin_headers,
        json={"name": "P", "category_id": cat["id"]},
    )).json()
    var = (await client.post(
        f"/api/v1/products/{prod['id']}/variants", headers=admin_headers,
        json={"size": "M", "color": "Q",
              "wholesale_price": "1000", "retail_price": "1500"},
    )).json()
    wh = (await client.post(
        "/api/v1/warehouses", headers=admin_headers,
        json={"name": "W", "code": "W"},
    )).json()
    cust = (await client.post(
        "/api/v1/customers", headers=admin_headers,
        json={"name": "M", "credit_limit": "100000"},
    )).json()

    await client.post(
        "/api/v1/orders", headers=admin_headers,
        json={"customer_id": cust["id"], "warehouse_id": wh["id"],
              "items": [{"variant_id": var["id"], "quantity": 3}]},
    )

    notifs = (await test_db.execute(
        select(Notification).where(Notification.type == NotificationType.NEW_ORDER)
    )).scalars().all()
    assert len(notifs) == 1
    assert "Yangi buyurtma" in notifs[0].title
    assert notifs[0].user_id is None  # broadcast

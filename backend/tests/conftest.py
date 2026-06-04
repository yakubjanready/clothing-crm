"""Umumiy test fixtures: aiosqlite engine, fakeredis va dependency overridelar."""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.models  # noqa: F401 — Base.metadata'ga modellarni registratsiya qilish
from app.api.deps import get_current_user
from app.core.redis import get_redis
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.permission import Permission
from app.models.role import Role, RoleName
from app.models.user import User


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_db(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    Session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest.fixture
async def fake_redis() -> AsyncGenerator[FakeRedis, None]:
    r = FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


@pytest.fixture
async def client(
    test_db: AsyncSession, fake_redis: FakeRedis
) -> AsyncGenerator[AsyncClient, None]:
    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db

    def _override_redis() -> FakeRedis:
        return fake_redis

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---- RBAC seed fixtures ----

async def _seed_rbac(db: AsyncSession) -> dict[str, Role]:
    """Minimal RBAC: admin va sales rollari + bir nechta permission (HR ham)."""
    perm_codes = [
        "user:read", "user:write", "user:delete",
        "customer:read", "order:read",
        "hr:read", "hr:write", "hr:delete", "audit:read",
    ]
    perms = {code: Permission(code=code, description=code) for code in perm_codes}
    for p in perms.values():
        db.add(p)
    await db.flush()

    admin = Role(name=RoleName.ADMIN, description="admin")
    admin.permissions = list(perms.values())

    sales = Role(name=RoleName.SALES, description="sales")
    sales.permissions = [perms["customer:read"], perms["order:read"]]

    db.add_all([admin, sales])
    await db.commit()
    return {RoleName.ADMIN: admin, RoleName.SALES: sales}


@pytest.fixture
async def seeded_roles(test_db: AsyncSession) -> dict[str, Role]:
    return await _seed_rbac(test_db)


@pytest.fixture
async def admin_user(test_db: AsyncSession, seeded_roles: dict[str, Role]) -> User:
    u = User(
        email="admin@example.com",
        full_name="Test Admin",
        hashed_password=hash_password("AdminPass123!"),
        is_active=True,
        roles=[seeded_roles[RoleName.ADMIN]],
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u, attribute_names=["roles"])
    return u


@pytest.fixture
async def sales_user(test_db: AsyncSession, seeded_roles: dict[str, Role]) -> User:
    u = User(
        email="sales@example.com",
        full_name="Test Sales",
        hashed_password=hash_password("SalesPass123!"),
        is_active=True,
        roles=[seeded_roles[RoleName.SALES]],
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u, attribute_names=["roles"])
    return u


def override_user(u: User) -> None:
    """get_current_user'ni majburlab boshqa user'ga aylantirish (permission testlari uchun)."""
    async def _u() -> User:
        return u

    app.dependency_overrides[get_current_user] = _u

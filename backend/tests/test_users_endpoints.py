"""/users va /roles endpointlari uchun integratsion testlar.

Qamrov:
- list (search, role filter, is_active filter, paginate, include_deleted)
- get (404)
- patch (full_name, is_active, role_ids) + audit yozuvi
- patch o'zini deaktiv qilishni rad etadi
- patch o'zining rolini o'zgartirishni rad etadi
- soft-delete + restore
- soft-delete o'zini o'chirishni rad etadi
- reset-password — parol o'zgaradi, eski parol bilan login bo'lmaydi
- /roles — permission code'lari bilan
- sales user → barcha admin endpointlarda 403
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.activity_log import ActivityLog
from app.models.role import Role, RoleName
from app.models.user import User


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def sales_headers(client: AsyncClient, sales_user: User) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "sales@example.com", "password": "SalesPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def extra_user(test_db: AsyncSession, seeded_roles: dict[str, Role]) -> User:
    u = User(
        email="bob@example.com",
        full_name="Bob Tester",
        hashed_password=hash_password("BobPass123!"),
        is_active=True,
        roles=[seeded_roles[RoleName.SALES]],
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u, attribute_names=["roles"])
    return u


# ============ LIST ============


async def test_list_users_returns_paginated(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    extra_user: User,
) -> None:
    resp = await client.get("/api/v1/users", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert body["page"] == 1
    emails = {u["email"] for u in body["items"]}
    assert emails == {"admin@example.com", "bob@example.com"}


async def test_list_users_search(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    extra_user: User,
) -> None:
    resp = await client.get("/api/v1/users", headers=admin_headers, params={"search": "bob"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "bob@example.com"


async def test_list_users_filter_by_role(
    client: AsyncClient,
    admin_headers: dict[str, str],
    seeded_roles: dict[str, Role],
    admin_user: User,
    extra_user: User,
) -> None:
    sales_role_id = str(seeded_roles[RoleName.SALES].id)
    resp = await client.get(
        "/api/v1/users",
        headers=admin_headers,
        params={"role_id": sales_role_id},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "bob@example.com"


async def test_list_users_filter_is_active(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    extra_user: User,
    test_db: AsyncSession,
) -> None:
    extra_user.is_active = False
    await test_db.commit()
    resp = await client.get("/api/v1/users", headers=admin_headers, params={"is_active": "false"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "bob@example.com"


async def test_list_users_requires_user_read(
    client: AsyncClient, sales_headers: dict[str, str]
) -> None:
    resp = await client.get("/api/v1/users", headers=sales_headers)
    assert resp.status_code == 403


# ============ GET ============


async def test_get_user_ok(
    client: AsyncClient, admin_headers: dict[str, str], extra_user: User
) -> None:
    resp = await client.get(f"/api/v1/users/{extra_user.id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == "bob@example.com"


async def test_get_user_404(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    resp = await client.get(
        "/api/v1/users/00000000-0000-0000-0000-000000000000", headers=admin_headers
    )
    assert resp.status_code == 404


# ============ PATCH ============


async def test_patch_user_full_name_and_audit(
    client: AsyncClient,
    admin_headers: dict[str, str],
    extra_user: User,
    test_db: AsyncSession,
) -> None:
    resp = await client.patch(
        f"/api/v1/users/{extra_user.id}",
        headers=admin_headers,
        json={"full_name": "Bob Yangi"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["full_name"] == "Bob Yangi"

    logs = (
        (
            await test_db.execute(
                select(ActivityLog).where(
                    ActivityLog.entity_type == "user",
                    ActivityLog.entity_id == extra_user.id,
                    ActivityLog.action == "update",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].changes["full_name"]["new"] == "Bob Yangi"


async def test_patch_user_change_roles(
    client: AsyncClient,
    admin_headers: dict[str, str],
    extra_user: User,
    seeded_roles: dict[str, Role],
) -> None:
    admin_role_id = str(seeded_roles[RoleName.ADMIN].id)
    resp = await client.patch(
        f"/api/v1/users/{extra_user.id}",
        headers=admin_headers,
        json={"role_ids": [admin_role_id]},
    )
    assert resp.status_code == 200, resp.text
    role_names = {r["name"] for r in resp.json()["roles"]}
    assert role_names == {RoleName.ADMIN}


async def test_patch_user_invalid_role_400(
    client: AsyncClient, admin_headers: dict[str, str], extra_user: User
) -> None:
    resp = await client.patch(
        f"/api/v1/users/{extra_user.id}",
        headers=admin_headers,
        json={"role_ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    assert resp.status_code == 400


async def test_patch_self_deactivate_blocked(
    client: AsyncClient, admin_headers: dict[str, str], admin_user: User
) -> None:
    resp = await client.patch(
        f"/api/v1/users/{admin_user.id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 400
    assert "o'zingizni" in resp.json()["detail"].lower()


async def test_patch_self_role_change_blocked(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    seeded_roles: dict[str, Role],
) -> None:
    sales_role_id = str(seeded_roles[RoleName.SALES].id)
    resp = await client.patch(
        f"/api/v1/users/{admin_user.id}",
        headers=admin_headers,
        json={"role_ids": [sales_role_id]},
    )
    assert resp.status_code == 400


async def test_patch_requires_user_write(
    client: AsyncClient, sales_headers: dict[str, str], extra_user: User
) -> None:
    resp = await client.patch(
        f"/api/v1/users/{extra_user.id}",
        headers=sales_headers,
        json={"full_name": "Hack"},
    )
    assert resp.status_code == 403


# ============ DELETE / RESTORE ============


async def test_soft_delete_then_restore(
    client: AsyncClient,
    admin_headers: dict[str, str],
    extra_user: User,
) -> None:
    d = await client.delete(f"/api/v1/users/{extra_user.id}", headers=admin_headers)
    assert d.status_code == 204

    # ro'yxatda chiqmaydi
    listed = await client.get("/api/v1/users", headers=admin_headers)
    emails = {u["email"] for u in listed.json()["items"]}
    assert "bob@example.com" not in emails

    # include_deleted bilan chiqadi
    listed_all = await client.get(
        "/api/v1/users", headers=admin_headers, params={"include_deleted": "true"}
    )
    emails_all = {u["email"] for u in listed_all.json()["items"]}
    assert "bob@example.com" in emails_all

    # restore
    r = await client.post(f"/api/v1/users/{extra_user.id}/restore", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["is_active"] is True


async def test_soft_delete_self_blocked(
    client: AsyncClient, admin_headers: dict[str, str], admin_user: User
) -> None:
    resp = await client.delete(f"/api/v1/users/{admin_user.id}", headers=admin_headers)
    assert resp.status_code == 400


# ============ RESET PASSWORD ============


async def test_reset_password_changes_login(
    client: AsyncClient,
    admin_headers: dict[str, str],
    extra_user: User,
) -> None:
    new_pw = "BrandNew456!"
    resp = await client.post(
        f"/api/v1/users/{extra_user.id}/reset-password",
        headers=admin_headers,
        json={"password": new_pw},
    )
    assert resp.status_code == 204

    # eski parol bilan login ishlamaydi
    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "BobPass123!"},
    )
    assert bad.status_code == 401

    # yangi parol bilan login ishlaydi
    good = await client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": new_pw},
    )
    assert good.status_code == 200, good.text


async def test_reset_password_short_password_422(
    client: AsyncClient, admin_headers: dict[str, str], extra_user: User
) -> None:
    resp = await client.post(
        f"/api/v1/users/{extra_user.id}/reset-password",
        headers=admin_headers,
        json={"password": "short"},
    )
    assert resp.status_code == 422


# ============ ROLES ============


async def test_list_roles_includes_permissions(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.get("/api/v1/roles", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    names = {r["name"] for r in body}
    assert {RoleName.ADMIN, RoleName.SALES}.issubset(names)
    admin_row = next(r for r in body if r["name"] == RoleName.ADMIN)
    assert "user:write" in admin_row["permission_codes"]
    sales_row = next(r for r in body if r["name"] == RoleName.SALES)
    assert "order:approve" not in sales_row["permission_codes"]


async def test_my_permissions_returns_codes(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.get("/api/v1/users/me/permissions", headers=admin_headers)
    assert resp.status_code == 200
    codes = resp.json()
    assert "user:write" in codes
    assert "hr:read" in codes

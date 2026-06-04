"""/auth/* endpointlari uchun integratsion testlar (aiosqlite + fakeredis)."""
from __future__ import annotations

from httpx import AsyncClient

from app.models.role import RoleName
from app.models.user import User


# ---- login ----

async def test_login_success_returns_token_pair(
    client: AsyncClient, admin_user: User
) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 50
    assert isinstance(body["refresh_token"], str) and len(body["refresh_token"]) > 50
    assert body["access_token"] != body["refresh_token"]


async def test_login_wrong_password_401(
    client: AsyncClient, admin_user: User
) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401


async def test_login_unknown_email_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "x"},
    )
    assert resp.status_code == 401


async def test_login_inactive_user_401(
    client: AsyncClient, admin_user: User, test_db
) -> None:
    admin_user.is_active = False
    await test_db.commit()
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    assert resp.status_code == 401


# ---- /me ----

async def test_me_returns_current_user(
    client: AsyncClient, admin_user: User
) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    access = login.json()["access_token"]
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert resp.status_code == 200
    me = resp.json()
    assert me["email"] == "admin@example.com"
    assert me["is_active"] is True
    assert {r["name"] for r in me["roles"]} == {RoleName.ADMIN}


async def test_me_without_token_401(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_with_invalid_token_401(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert resp.status_code == 401


# ---- refresh rotation ----

async def test_refresh_rotates_and_invalidates_old(
    client: AsyncClient, admin_user: User
) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    refresh_1 = login.json()["refresh_token"]

    r1 = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_1}
    )
    assert r1.status_code == 200, r1.text
    refresh_2 = r1.json()["refresh_token"]
    assert refresh_2 != refresh_1

    # Eski refresh endi yaroqsiz
    r2 = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_1}
    )
    assert r2.status_code == 401


async def test_refresh_with_access_token_rejected(
    client: AsyncClient, admin_user: User
) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    access = login.json()["access_token"]
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": access}
    )
    assert resp.status_code == 401


# ---- logout ----

async def test_logout_revokes_all_refresh_tokens(
    client: AsyncClient, admin_user: User
) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    access = login.json()["access_token"]
    refresh = login.json()["refresh_token"]

    logout = await client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {access}"}
    )
    assert logout.status_code == 204

    # Logout'dan keyin refresh ham bekor qilingan
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh}
    )
    assert resp.status_code == 401


# ---- register (admin only) ----

async def test_register_as_admin_creates_user(
    client: AsyncClient, admin_user: User
) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    access = login.json()["access_token"]

    resp = await client.post(
        "/api/v1/auth/register",
        headers={"Authorization": f"Bearer {access}"},
        json={
            "email": "newuser@example.com",
            "full_name": "Yangi Foydalanuvchi",
            "password": "NewPass123!",
        },
    )
    assert resp.status_code == 201, resp.text
    new_user = resp.json()
    assert new_user["email"] == "newuser@example.com"
    assert new_user["is_active"] is True
    assert new_user["roles"] == []


async def test_register_as_sales_forbidden(
    client: AsyncClient, sales_user: User
) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "sales@example.com", "password": "SalesPass123!"},
    )
    access = login.json()["access_token"]

    resp = await client.post(
        "/api/v1/auth/register",
        headers={"Authorization": f"Bearer {access}"},
        json={
            "email": "x@example.com",
            "full_name": "X",
            "password": "XXXXXXXX",
        },
    )
    assert resp.status_code == 403
    assert "user:write" in resp.json()["detail"]


async def test_register_duplicate_email_409(
    client: AsyncClient, admin_user: User
) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    access = login.json()["access_token"]

    payload = {
        "email": "dup@example.com",
        "full_name": "Dup",
        "password": "DupPass123!",
    }
    first = await client.post(
        "/api/v1/auth/register",
        headers={"Authorization": f"Bearer {access}"},
        json=payload,
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/auth/register",
        headers={"Authorization": f"Bearer {access}"},
        json=payload,
    )
    assert second.status_code == 409



"""HR CRUD endpointlari uchun integratsion testlar (aiosqlite + fakeredis).
Audit yozish va permission tekshirish ham shu yerda."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.department import Department
from app.models.employee import EmployeeStatus
from app.models.position import Position
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


# ============ Departments ============


async def test_create_department_writes_audit(
    client: AsyncClient, admin_headers: dict[str, str], test_db: AsyncSession
) -> None:
    resp = await client.post(
        "/api/v1/hr/departments",
        headers=admin_headers,
        json={"name": "Sotuv", "code": "SLS", "description": "Sotuv bo'limi"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Sotuv"
    assert body["code"] == "SLS"

    # Audit
    logs = (
        (await test_db.execute(select(ActivityLog).where(ActivityLog.entity_type == "department")))
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].action == "create"
    assert logs[0].changes["name"] == "Sotuv"


async def test_department_parent_child_tree(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    parent = (
        await client.post(
            "/api/v1/hr/departments",
            headers=admin_headers,
            json={"name": "Bosh ofis", "code": "HQ"},
        )
    ).json()
    child = await client.post(
        "/api/v1/hr/departments",
        headers=admin_headers,
        json={"name": "IT", "code": "IT", "parent_id": parent["id"]},
    )
    assert child.status_code == 201
    assert child.json()["parent_id"] == parent["id"]

    listed = await client.get(
        "/api/v1/hr/departments",
        headers=admin_headers,
        params={"parent_id": parent["id"]},
    )
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1 and items[0]["name"] == "IT"


async def test_department_self_parent_rejected(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    dept = (
        await client.post(
            "/api/v1/hr/departments",
            headers=admin_headers,
            json={"name": "Loop"},
        )
    ).json()
    resp = await client.patch(
        f"/api/v1/hr/departments/{dept['id']}",
        headers=admin_headers,
        json={"parent_id": dept["id"]},
    )
    assert resp.status_code == 400


async def test_department_soft_delete_and_restore(
    client: AsyncClient, admin_headers: dict[str, str], test_db: AsyncSession
) -> None:
    dept = (
        await client.post(
            "/api/v1/hr/departments",
            headers=admin_headers,
            json={"name": "Temp"},
        )
    ).json()

    # delete
    d = await client.delete(f"/api/v1/hr/departments/{dept['id']}", headers=admin_headers)
    assert d.status_code == 204

    # default list — yo'q
    listed = await client.get("/api/v1/hr/departments", headers=admin_headers)
    assert all(it["id"] != dept["id"] for it in listed.json()["items"])

    # include_deleted=true — bor
    listed_all = await client.get(
        "/api/v1/hr/departments",
        headers=admin_headers,
        params={"include_deleted": "true"},
    )
    assert any(it["id"] == dept["id"] for it in listed_all.json()["items"])

    # restore
    r = await client.post(f"/api/v1/hr/departments/{dept['id']}/restore", headers=admin_headers)
    assert r.status_code == 200

    # audit izlari: create, soft_delete, restore
    actions = [
        l.action
        for l in (
            await test_db.execute(
                select(ActivityLog)
                .where(ActivityLog.entity_type == "department")
                .order_by(ActivityLog.created_at)
            )
        )
        .scalars()
        .all()
    ]
    assert actions == ["create", "soft_delete", "restore"]


# ============ Permissions ============


async def test_sales_user_cannot_write_hr(
    client: AsyncClient, sales_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/v1/hr/departments",
        headers=sales_headers,
        json={"name": "Hujum"},
    )
    assert resp.status_code == 403
    assert "hr:write" in resp.json()["detail"]


async def test_sales_user_cannot_read_audit(
    client: AsyncClient, sales_headers: dict[str, str]
) -> None:
    resp = await client.get("/api/v1/hr/audit-logs", headers=sales_headers)
    assert resp.status_code == 403


# ============ Positions ============


async def test_create_position_with_salary(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    dept = (
        await client.post("/api/v1/hr/departments", headers=admin_headers, json={"name": "Sotuv"})
    ).json()

    resp = await client.post(
        "/api/v1/hr/positions",
        headers=admin_headers,
        json={
            "name": "Sotuv menejeri",
            "base_salary": "5000000.00",
            "department_id": dept["id"],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["base_salary"] == "5000000.00"
    assert body["department_id"] == dept["id"]


async def test_update_position_salary_logs_diff(
    client: AsyncClient, admin_headers: dict[str, str], test_db: AsyncSession
) -> None:
    pos = (
        await client.post(
            "/api/v1/hr/positions",
            headers=admin_headers,
            json={"name": "Operator", "base_salary": "3000000"},
        )
    ).json()

    upd = await client.patch(
        f"/api/v1/hr/positions/{pos['id']}",
        headers=admin_headers,
        json={"base_salary": "3500000"},
    )
    assert upd.status_code == 200

    log = (
        await test_db.execute(
            select(ActivityLog).where(
                ActivityLog.entity_type == "position", ActivityLog.action == "update"
            )
        )
    ).scalar_one()
    assert "base_salary" in log.changes
    # jsonable_encoder Decimal'ni float'ga aylantiradi
    assert float(log.changes["base_salary"]["old"]) == 3000000.0
    assert float(log.changes["base_salary"]["new"]) == 3500000.0


# ============ Employees ============


@pytest.fixture
async def dept_and_pos(client: AsyncClient, admin_headers: dict[str, str]) -> tuple[str, str]:
    d = (
        await client.post("/api/v1/hr/departments", headers=admin_headers, json={"name": "Magazin"})
    ).json()
    p = (
        await client.post(
            "/api/v1/hr/positions",
            headers=admin_headers,
            json={"name": "Sotuvchi", "base_salary": "4000000", "department_id": d["id"]},
        )
    ).json()
    return d["id"], p["id"]


async def test_create_employee(
    client: AsyncClient, admin_headers: dict[str, str], dept_and_pos: tuple[str, str]
) -> None:
    dept_id, pos_id = dept_and_pos
    resp = await client.post(
        "/api/v1/hr/employees",
        headers=admin_headers,
        json={
            "first_name": "Alisher",
            "last_name": "Karimov",
            "email": "alisher@example.com",
            "phone": "+998901234567",
            "photo_url": "https://cdn.example.com/p/alisher.jpg",
            "status": "active",
            "department_id": dept_id,
            "position_id": pos_id,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["first_name"] == "Alisher"
    assert body["status"] == "active"
    assert body["photo_url"].endswith("alisher.jpg")


async def test_employee_filter_by_status_and_search(
    client: AsyncClient, admin_headers: dict[str, str], dept_and_pos: tuple[str, str]
) -> None:
    dept_id, pos_id = dept_and_pos

    payload = {
        "department_id": dept_id,
        "position_id": pos_id,
        "status": "active",
    }
    for fn, ln, em, st in [
        ("Alisher", "Karimov", "a@example.com", "active"),
        ("Bobur", "Karimov", "b@example.com", "on_leave"),
        ("Diyor", "Yo'ldoshev", "d@example.com", "active"),
    ]:
        await client.post(
            "/api/v1/hr/employees",
            headers=admin_headers,
            json={**payload, "first_name": fn, "last_name": ln, "email": em, "status": st},
        )

    # Status filtri
    only_active = await client.get(
        "/api/v1/hr/employees", headers=admin_headers, params={"status": "active"}
    )
    assert only_active.json()["total"] == 2

    # Search (last_name)
    karims = await client.get(
        "/api/v1/hr/employees", headers=admin_headers, params={"search": "karim"}
    )
    assert karims.json()["total"] == 2

    # Search (email)
    by_email = await client.get(
        "/api/v1/hr/employees", headers=admin_headers, params={"search": "d@example"}
    )
    assert by_email.json()["total"] == 1 and by_email.json()["items"][0]["first_name"] == "Diyor"


async def test_employee_pagination(
    client: AsyncClient, admin_headers: dict[str, str], dept_and_pos: tuple[str, str]
) -> None:
    dept_id, pos_id = dept_and_pos
    for i in range(12):
        await client.post(
            "/api/v1/hr/employees",
            headers=admin_headers,
            json={
                "first_name": f"Xodim{i:02d}",
                "last_name": "Test",
                "email": f"u{i:02d}@example.com",
                "department_id": dept_id,
                "position_id": pos_id,
            },
        )

    p1 = (
        await client.get(
            "/api/v1/hr/employees",
            headers=admin_headers,
            params={"page": 1, "page_size": 5},
        )
    ).json()
    assert p1["total"] == 12 and p1["pages"] == 3 and len(p1["items"]) == 5

    p3 = (
        await client.get(
            "/api/v1/hr/employees",
            headers=admin_headers,
            params={"page": 3, "page_size": 5},
        )
    ).json()
    assert len(p3["items"]) == 2


async def test_employee_invalid_department_400(
    client: AsyncClient, admin_headers: dict[str, str], dept_and_pos: tuple[str, str]
) -> None:
    _, pos_id = dept_and_pos
    resp = await client.post(
        "/api/v1/hr/employees",
        headers=admin_headers,
        json={
            "first_name": "X",
            "last_name": "Y",
            "department_id": "00000000-0000-0000-0000-000000000000",
            "position_id": pos_id,
        },
    )
    assert resp.status_code == 400


# ============ Audit log endpoint ============


async def test_audit_log_endpoint_filters(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await client.post("/api/v1/hr/departments", headers=admin_headers, json={"name": "A"})
    await client.post("/api/v1/hr/departments", headers=admin_headers, json={"name": "B"})
    resp = await client.get(
        "/api/v1/hr/audit-logs",
        headers=admin_headers,
        params={"entity_type": "department", "action": "create"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


# ============ Direct model checks ============


def test_models_loaded_correctly() -> None:
    assert Department.__tablename__ == "departments"
    assert Position.__tablename__ == "positions"
    assert "base_salary" in {c.name for c in Position.__table__.columns}
    assert "photo_url" in {
        c.name for c in __import__("app.models", fromlist=["Employee"]).Employee.__table__.columns
    }
    assert EmployeeStatus.ACTIVE == "active"
    assert ActivityLog.__tablename__ == "activity_logs"

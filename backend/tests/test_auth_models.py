"""Auth modellari sxema testlari (kichik, tez)."""
from __future__ import annotations

from app.models.permission import Permission
from app.models.role import Role, RoleName
from app.models.user import User


def test_role_name_enum_has_seven_roles() -> None:
    assert set(RoleName) == {
        RoleName.ADMIN,
        RoleName.DIRECTOR,
        RoleName.MANAGER,
        RoleName.SALES,
        RoleName.WAREHOUSE,
        RoleName.ACCOUNTANT,
        RoleName.COURIER,
    }
    assert RoleName.ADMIN.value == "admin"
    assert RoleName.COURIER.value == "courier"


def test_user_table_has_auth_columns() -> None:
    cols = {c.name for c in User.__table__.columns}
    expected = {
        "id", "email", "full_name", "hashed_password", "is_active",
        "created_at", "updated_at", "deleted_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"

    email = User.__table__.c.email
    assert email.unique is True
    assert email.index is True
    assert email.nullable is False


def test_role_table_has_unique_name() -> None:
    role_name = Role.__table__.c.name
    assert role_name.unique is True
    assert role_name.nullable is False


def test_permission_table_has_unique_code() -> None:
    code = Permission.__table__.c.code
    assert code.unique is True
    assert code.nullable is False


def test_m2m_tables_registered_in_metadata() -> None:
    from app.db.base import Base
    tables = set(Base.metadata.tables.keys())
    assert "user_roles" in tables
    assert "role_permissions" in tables
    assert "users" in tables
    assert "roles" in tables
    assert "permissions" in tables


def test_user_permission_codes_aggregates_from_roles() -> None:
    p1 = Permission(code="customer:read", description="")
    p2 = Permission(code="order:read", description="")
    r1 = Role(name="r1", description=""); r1.permissions = [p1]
    r2 = Role(name="r2", description=""); r2.permissions = [p2, p1]
    u = User(
        email="u@x.x", full_name="u",
        hashed_password="x", is_active=True,
    )
    u.roles = [r1, r2]
    assert u.permission_codes == {"customer:read", "order:read"}
    assert u.role_names == {"r1", "r2"}

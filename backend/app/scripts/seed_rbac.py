"""RBAC seed scripti — idempotent.

Yaratadi:
- 15 ta permission (CRM modullari uchun)
- 7 ta rol (admin/director/manager/sales/warehouse/accountant/courier)
- role-permission mapping
- boshlang'ich admin user (INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD'dan)

Ishga tushirish:
    python -m app.scripts.seed_rbac
    docker compose exec backend python -m app.scripts.seed_rbac
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, dispose_engine
from app.models.permission import Permission
from app.models.role import Role, RoleName
from app.models.user import User


PERMISSIONS: list[tuple[str, str]] = [
    ("user:read",       "Foydalanuvchilarni ko'rish"),
    ("user:write",      "Foydalanuvchi qo'shish/tahrirlash"),
    ("user:delete",     "Foydalanuvchini o'chirish"),
    ("customer:read",   "Mijozlarni va aloqalarni ko'rish"),
    ("customer:write",  "Mijoz/kontakt/aloqa qo'shish/tahrirlash"),
    ("customer:delete", "Mijozni yumshoq o'chirish"),
    ("product:read",    "Mahsulot/kategoriya/brendni ko'rish"),
    ("product:write",   "Mahsulot/kategoriya/brendni qo'shish/tahrirlash + rasm yuklash"),
    ("product:delete",  "Mahsulot/kategoriya/brendni yumshoq o'chirish"),
    ("order:read",      "Buyurtmalarni ko'rish"),
    ("order:write",     "Buyurtma yaratish/tahrirlash"),
    ("order:approve",   "Buyurtmani tasdiqlash"),
    ("warehouse:read",  "Omborni ko'rish"),
    ("warehouse:write", "Ombor amallari (kirim/chiqim)"),
    ("accounting:read", "Hisob-kitobni ko'rish"),
    ("accounting:write","Hisob-kitob yozish"),
    ("report:read",     "Hisobotlarni ko'rish"),
    ("hr:read",         "HR — xodimlar/bo'lim/lavozimlarni ko'rish"),
    ("hr:write",        "HR — yaratish/tahrirlash/restore"),
    ("hr:delete",       "HR — yumshoq o'chirish"),
    ("audit:read",      "Audit jurnalini ko'rish"),
]

ALL = [p[0] for p in PERMISSIONS]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    RoleName.ADMIN: ALL,
    RoleName.DIRECTOR: [
        "user:read",
        "customer:read", "product:read",
        "order:read", "order:approve",
        "warehouse:read", "accounting:read", "report:read",
        "hr:read", "audit:read",
    ],
    RoleName.MANAGER: [
        "customer:read", "customer:write",
        "product:read",
        "order:read", "order:write", "order:approve",
        "warehouse:read", "report:read",
        "hr:read", "hr:write",
    ],
    RoleName.SALES: [
        "customer:read", "customer:write",
        "product:read",
        "order:read", "order:write",
    ],
    RoleName.WAREHOUSE: [
        "warehouse:read", "warehouse:write",
        "product:read", "product:write",
        "order:read",
    ],
    # ESLATMA: product:delete faqat admin'da (default ALL ichida)
    RoleName.ACCOUNTANT: [
        "customer:read",
        "order:read",
        "accounting:read", "accounting:write",
        "report:read",
    ],
    RoleName.COURIER: [
        "order:read",
    ],
}


async def _upsert_permissions(db: AsyncSession) -> dict[str, Permission]:
    existing = (await db.execute(select(Permission))).scalars().all()
    by_code = {p.code: p for p in existing}
    for code, desc in PERMISSIONS:
        if code not in by_code:
            p = Permission(code=code, description=desc)
            db.add(p)
            by_code[code] = p
    await db.commit()
    return by_code


async def _upsert_roles(
    db: AsyncSession, perms_by_code: dict[str, Permission]
) -> dict[str, Role]:
    existing = (
        await db.execute(select(Role).options(selectinload(Role.permissions)))
    ).scalars().all()
    by_name = {r.name: r for r in existing}

    for role_name, codes in ROLE_PERMISSIONS.items():
        role = by_name.get(role_name)
        if role is None:
            role = Role(name=role_name, description=f"{role_name} rol")
            db.add(role)
            by_name[role_name] = role
        role.permissions = [perms_by_code[c] for c in codes]
    await db.commit()
    return by_name


async def _ensure_admin_user(
    db: AsyncSession, admin_role: Role
) -> tuple[User, bool]:
    res = await db.execute(
        select(User)
        .where(User.email == settings.INITIAL_ADMIN_EMAIL)
        .options(selectinload(User.roles))
    )
    user = res.scalar_one_or_none()
    if user is not None:
        return user, False

    user = User(
        email=settings.INITIAL_ADMIN_EMAIL,
        full_name="Boshlang'ich administrator",
        hashed_password=hash_password(settings.INITIAL_ADMIN_PASSWORD),
        is_active=True,
        roles=[admin_role],
    )
    db.add(user)
    await db.commit()
    return user, True


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        perms = await _upsert_permissions(db)
        print(f"[seed] permissions ready: {len(perms)}")

        roles = await _upsert_roles(db, perms)
        print(f"[seed] roles ready: {len(roles)}  ({', '.join(sorted(roles))})")

        admin_role = roles[RoleName.ADMIN]
        admin_user, created = await _ensure_admin_user(db, admin_role)
        marker = "yaratildi" if created else "mavjud"
        print(f"[seed] admin user {marker}: {admin_user.email}")

    await dispose_engine()
    print("[seed] tugadi")


if __name__ == "__main__":
    asyncio.run(seed())

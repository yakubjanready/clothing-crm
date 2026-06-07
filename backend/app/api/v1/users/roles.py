"""/roles — rollar va permission'lar ro'yxati (faqat o'qish)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.user import RoleListRead

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleListRead])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("user:read")),
) -> list[RoleListRead]:
    stmt = select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        RoleListRead(
            id=r.id,
            name=r.name,
            description=r.description,
            permission_codes=sorted(p.code for p in r.permissions),
        )
        for r in rows
    ]

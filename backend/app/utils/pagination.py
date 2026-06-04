"""Sahifalash yordamchilari — query param + javob konvert."""
from __future__ import annotations

import math
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(1, ge=1, description="Sahifa raqami (1 dan boshlanadi)")
    page_size: int = Field(20, ge=1, le=100, description="Sahifadagi yozuvlar soni")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PageParams:
    """FastAPI dependency — query param'lardan PageParams."""
    return PageParams(page=page, page_size=page_size)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


async def paginate(
    db: AsyncSession,
    stmt: Select,
    params: PageParams,
) -> tuple[list, int, int]:
    """`stmt`'ni paginate qiladi va `(items, total, pages)` qaytaradi.
    Routerda Page[ReadSchema](...).model_validate orqali tugatish kerak.
    """
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    items_stmt = stmt.offset(params.offset).limit(params.page_size)
    items = (await db.execute(items_stmt)).scalars().unique().all()

    pages = math.ceil(total / params.page_size) if total else 0
    return list(items), total, pages

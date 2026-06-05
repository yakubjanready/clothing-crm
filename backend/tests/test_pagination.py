"""utils/pagination.py — birlik testlar."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission
from app.utils.pagination import Page, PageParams, paginate


def test_page_params_offset_calculation() -> None:
    assert PageParams(page=1, page_size=20).offset == 0
    assert PageParams(page=2, page_size=20).offset == 20
    assert PageParams(page=5, page_size=50).offset == 200


async def test_paginate_returns_correct_slice_and_total(test_db: AsyncSession) -> None:
    # 25 ta permission qo'shamiz
    for i in range(25):
        test_db.add(Permission(code=f"p_{i:02d}", description=f"perm {i}"))
    await test_db.commit()

    params = PageParams(page=2, page_size=10)
    stmt = select(Permission).order_by(Permission.code)
    items, total, pages = await paginate(test_db, stmt, params)

    assert total == 25
    assert pages == 3
    assert len(items) == 10
    assert items[0].code == "p_10"
    assert items[-1].code == "p_19"


async def test_paginate_last_partial_page(test_db: AsyncSession) -> None:
    for i in range(7):
        test_db.add(Permission(code=f"q_{i}", description=""))
    await test_db.commit()

    items, total, pages = await paginate(
        test_db, select(Permission), PageParams(page=2, page_size=5)
    )
    assert total == 7
    assert pages == 2
    assert len(items) == 2  # 5+2


async def test_paginate_empty_set(test_db: AsyncSession) -> None:
    items, total, pages = await paginate(
        test_db, select(Permission), PageParams(page=1, page_size=10)
    )
    assert items == []
    assert total == 0
    assert pages == 0


def test_page_model_generic() -> None:
    p = Page[int](items=[1, 2, 3], total=3, page=1, page_size=10, pages=1)
    assert p.items == [1, 2, 3]
    assert p.total == 3

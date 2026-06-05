"""Markaziy test factories — qayta ishlatiluvchi yaratish helperlari.

Maqsad: testlarda 5-10 qator setup kodini qaytarmaslik. Har funksiya
`db: AsyncSession` qabul qiladi, `await db.commit()` ni o'zi qiladi.

Ishlatish:
    from tests.factories import make_category, make_product, make_warehouse

    cat = await make_category(test_db, name="Maykalar")
    prod = await make_product(test_db, category_id=cat.id)
"""

from __future__ import annotations

import uuid as _uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.brand import Brand
from app.models.category import Category
from app.models.customer import Customer, CustomerSegment, PriceType
from app.models.product import Gender, Product
from app.models.product_variant import ProductVariant
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse, WarehouseType

# ---- Counter helpers (har test izolyatsiyalangan in-memory DB) ----

_counter = 0


def _next_id(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"{prefix}-{_counter:04d}"


# ---- Catalog ----


async def make_category(
    db: AsyncSession,
    *,
    name: str | None = None,
    slug: str | None = None,
) -> Category:
    nm = name or _next_id("cat")
    c = Category(name=nm, slug=slug or nm.lower().replace(" ", "-"))
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def make_brand(
    db: AsyncSession,
    *,
    name: str | None = None,
) -> Brand:
    nm = name or _next_id("brand")
    b = Brand(name=nm, slug=nm.lower().replace(" ", "-"))
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def make_product(
    db: AsyncSession,
    *,
    category_id: _uuid.UUID | str | None = None,
    brand_id: _uuid.UUID | str | None = None,
    name: str | None = None,
    gender: Gender = Gender.UNISEX,
) -> Product:
    if category_id is None:
        category_id = (await make_category(db)).id
    nm = name or _next_id("product")
    slug = nm.lower().replace(" ", "-")
    p = Product(
        name=nm,
        slug=slug,
        sku_prefix=slug.upper()[:6] + "-001",
        gender=gender,
        category_id=(
            category_id if isinstance(category_id, _uuid.UUID) else _uuid.UUID(str(category_id))
        ),
        brand_id=(
            brand_id
            if (brand_id is None or isinstance(brand_id, _uuid.UUID))
            else _uuid.UUID(str(brand_id))
        ),
        images=[],
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def make_variant(
    db: AsyncSession,
    *,
    product_id: _uuid.UUID | str,
    size: str = "M",
    color: str = "Qora",
    wholesale_price: Decimal = Decimal("1000"),
    retail_price: Decimal = Decimal("1500"),
) -> ProductVariant:
    pid = product_id if isinstance(product_id, _uuid.UUID) else _uuid.UUID(str(product_id))
    sku = _next_id("SKU")
    v = ProductVariant(
        product_id=pid,
        sku=sku,
        size=size,
        color=color,
        wholesale_price=wholesale_price,
        retail_price=retail_price,
    )
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return v


# ---- Warehouse ----


async def make_warehouse(
    db: AsyncSession,
    *,
    name: str | None = None,
    code: str | None = None,
    type_: WarehouseType = WarehouseType.MAIN,
) -> Warehouse:
    nm = name or _next_id("wh")
    w = Warehouse(name=nm, code=code or nm.upper(), type=type_)
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return w


# ---- Customer / Supplier ----


async def make_customer(
    db: AsyncSession,
    *,
    name: str | None = None,
    credit_limit: Decimal = Decimal("1000000"),
    segment: CustomerSegment = CustomerSegment.REGULAR,
    price_type: PriceType = PriceType.WHOLESALE,
) -> Customer:
    nm = name or _next_id("customer")
    c = Customer(
        name=nm,
        credit_limit=credit_limit,
        segment=segment,
        price_type=price_type,
        is_active=True,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def make_supplier(
    db: AsyncSession,
    *,
    name: str | None = None,
    rating: int = 4,
) -> Supplier:
    nm = name or _next_id("supplier")
    s = Supplier(name=nm, rating=rating, is_active=True)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


# ---- Finance ----


async def make_account(
    db: AsyncSession,
    *,
    name: str | None = None,
    type_: AccountType = AccountType.CASH,
    initial_balance: Decimal = Decimal("0"),
) -> Account:
    nm = name or _next_id("acc")
    a = Account(
        name=nm,
        type=type_,
        balance=initial_balance,
        currency="UZS",
        is_active=True,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a

"""Katalog endpointlari: /categories, /brands, /products, /products/{id}/variants, /upload/image."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.catalog.upload import get_media_root
from app.main import app
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.services.catalog import build_variant_sku, generate_sku_prefix, slugify

# ---- Helpers ----


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
def media_tmp(tmp_path: Path) -> Path:
    media = tmp_path / "media"
    media.mkdir()
    app.dependency_overrides[get_media_root] = lambda: media
    yield media
    app.dependency_overrides.pop(get_media_root, None)


@pytest.fixture
async def cat_brand(client: AsyncClient, admin_headers: dict[str, str]) -> tuple[str, str]:
    cat = (
        await client.post(
            "/api/v1/categories",
            headers=admin_headers,
            json={"name": "Maykalar"},
        )
    ).json()
    brand = (
        await client.post(
            "/api/v1/brands",
            headers=admin_headers,
            json={"name": "Nike", "country": "USA"},
        )
    ).json()
    return cat["id"], brand["id"]


# ============ services/catalog.py — pure ============


def test_slugify_handles_uzbek_and_punct() -> None:
    assert slugify("Mayka klassik!") == "mayka-klassik"
    assert slugify("   Bo'sh   ") == "bo-sh"
    assert slugify("Foo / Bar / Baz") == "foo-bar-baz"
    assert slugify("") == "item"


def test_generate_sku_prefix_format() -> None:
    p = generate_sku_prefix("Mayka klassik")
    base, suffix = p.split("-")
    assert base == "MAYKAK"
    assert len(suffix) == 4
    assert all(c in "0123456789ABCDEF" for c in suffix)


def test_generate_sku_prefix_unique_per_call() -> None:
    seen = {generate_sku_prefix("Mayka") for _ in range(50)}
    assert len(seen) == 50  # 16^4 ehtimol; 50 kollizionsiz


def test_build_variant_sku_deterministic() -> None:
    sku = build_variant_sku("NIKMAY-A1B2", "M", "Qora")
    assert sku == "NIKMAY-A1B2-M-QOR"
    sku2 = build_variant_sku("NIKMAY-A1B2", "XL", "OQ")
    assert sku2 == "NIKMAY-A1B2-XL-OQ"


# ============ Categories — tree ============


async def test_category_create_with_auto_slug(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Erkaklar kiyimi"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["slug"] == "erkaklar-kiyimi"


async def test_category_parent_child_tree(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    parent = (
        await client.post("/api/v1/categories", headers=admin_headers, json={"name": "Erkaklar"})
    ).json()
    child = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Maykalar", "parent_id": parent["id"]},
    )
    assert child.status_code == 201

    listed = await client.get(
        "/api/v1/categories",
        headers=admin_headers,
        params={"parent_id": parent["id"]},
    )
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["name"] == "Maykalar"


async def test_category_slug_unique_409(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Foo", "slug": "foo"},
    )
    dup = await client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Foo2", "slug": "foo"},
    )
    assert dup.status_code == 409


# ============ Brands ============


async def test_brand_create_and_filter_by_country(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await client.post(
        "/api/v1/brands",
        headers=admin_headers,
        json={"name": "Nike", "country": "USA"},
    )
    await client.post(
        "/api/v1/brands",
        headers=admin_headers,
        json={"name": "Adidas", "country": "DE"},
    )
    r = await client.get("/api/v1/brands", headers=admin_headers, params={"country": "USA"})
    assert r.json()["total"] == 1 and r.json()["items"][0]["name"] == "Nike"


# ============ Products ============


async def test_product_create_auto_sku_prefix(
    client: AsyncClient, admin_headers: dict[str, str], cat_brand: tuple[str, str]
) -> None:
    cat_id, brand_id = cat_brand
    r = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "name": "Mayka klassik",
            "gender": "men",
            "category_id": cat_id,
            "brand_id": brand_id,
            "images": ["/media/a.jpg", "/media/b.jpg"],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sku_prefix"].startswith("MAYKAK-")
    assert body["slug"] == "mayka-klassik"
    assert body["gender"] == "men"
    assert body["images"] == ["/media/a.jpg", "/media/b.jpg"]


async def test_product_filter_by_gender_brand_search(
    client: AsyncClient, admin_headers: dict[str, str], cat_brand: tuple[str, str]
) -> None:
    cat_id, brand_id = cat_brand
    other_brand = (
        await client.post("/api/v1/brands", headers=admin_headers, json={"name": "Puma"})
    ).json()

    for name, gender, b in [
        ("Mayka Erkak", "men", brand_id),
        ("Koylak Ayol", "women", brand_id),
        ("Sport Mayka", "men", other_brand["id"]),
    ]:
        await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={"name": name, "gender": gender, "category_id": cat_id, "brand_id": b},
        )

    men = await client.get("/api/v1/products", headers=admin_headers, params={"gender": "men"})
    assert men.json()["total"] == 2

    by_brand = await client.get(
        "/api/v1/products", headers=admin_headers, params={"brand_id": brand_id}
    )
    assert by_brand.json()["total"] == 2

    by_search = await client.get(
        "/api/v1/products", headers=admin_headers, params={"search": "sport"}
    )
    assert by_search.json()["total"] == 1


# ============ Variants — single + matrix ============


@pytest.fixture
async def product_id(
    client: AsyncClient, admin_headers: dict[str, str], cat_brand: tuple[str, str]
) -> str:
    cat_id, brand_id = cat_brand
    r = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"name": "Mayka", "gender": "unisex", "category_id": cat_id, "brand_id": brand_id},
    )
    return r.json()["id"]


async def test_create_single_variant_with_auto_sku(
    client: AsyncClient, admin_headers: dict[str, str], product_id: str
) -> None:
    r = await client.post(
        f"/api/v1/products/{product_id}/variants",
        headers=admin_headers,
        json={
            "size": "M",
            "color": "Qora",
            "wholesale_price": "120000",
            "retail_price": "180000",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sku"].endswith("-M-QOR")
    assert body["size"] == "M" and body["color"] == "Qora"


async def test_variant_size_color_unique(
    client: AsyncClient, admin_headers: dict[str, str], product_id: str
) -> None:
    payload = {"size": "M", "color": "Qora"}
    first = await client.post(
        f"/api/v1/products/{product_id}/variants",
        headers=admin_headers,
        json=payload,
    )
    assert first.status_code == 201
    dup = await client.post(
        f"/api/v1/products/{product_id}/variants",
        headers=admin_headers,
        json=payload,
    )
    assert dup.status_code == 409


async def test_variant_matrix_3_sizes_x_2_colors(
    client: AsyncClient, admin_headers: dict[str, str], product_id: str, test_db: AsyncSession
) -> None:
    r = await client.post(
        f"/api/v1/products/{product_id}/variants/matrix",
        headers=admin_headers,
        json={
            "sizes": ["S", "M", "L"],
            "colors": [
                {"name": "Qora", "hex": "#000000"},
                {"name": "Oq", "hex": "#FFFFFF"},
            ],
            "wholesale_price": "100000",
            "retail_price": "150000",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["created"]) == 6
    assert body["skipped_existing"] == []

    skus = {v["sku"] for v in body["created"]}
    assert len(skus) == 6  # SKU lar unique
    assert all("-" in s for s in skus)

    # DB tasdiqlash
    import uuid as _uuid

    rows = (
        (
            await test_db.execute(
                select(ProductVariant).where(ProductVariant.product_id == _uuid.UUID(product_id))
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 6


async def test_variant_matrix_skips_existing(
    client: AsyncClient, admin_headers: dict[str, str], product_id: str
) -> None:
    # Avval bitta variant qo'lda yaratamiz
    await client.post(
        f"/api/v1/products/{product_id}/variants",
        headers=admin_headers,
        json={"size": "M", "color": "Qora"},
    )
    # Matrix M/Qora ni o'tkazib yuborishi kerak
    r = await client.post(
        f"/api/v1/products/{product_id}/variants/matrix",
        headers=admin_headers,
        json={"sizes": ["S", "M"], "colors": [{"name": "Qora"}]},
    )
    body = r.json()
    assert len(body["created"]) == 1  # faqat S/Qora
    assert body["skipped_existing"] == [{"size": "M", "color": "Qora"}]


# ============ Permissions ============


async def test_sales_user_cannot_create_product(
    client: AsyncClient, sales_headers: dict[str, str], admin_headers: dict[str, str]
) -> None:
    # sales user kategoriya ham yarata olmaydi — lekin admin avval yaratadi
    cat = (
        await client.post("/api/v1/categories", headers=admin_headers, json={"name": "Foo"})
    ).json()
    r = await client.post(
        "/api/v1/products",
        headers=sales_headers,
        json={"name": "X", "category_id": cat["id"]},
    )
    assert r.status_code == 403


# ============ Image upload ============


async def test_upload_image_jpeg_success(
    client: AsyncClient, admin_headers: dict[str, str], media_tmp: Path
) -> None:
    fake_jpg = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # JPEG magic + padding
    files = {"file": ("test.jpg", io.BytesIO(fake_jpg), "image/jpeg")}
    r = await client.post("/api/v1/upload/image", headers=admin_headers, files=files)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["url"].startswith("/media/") and body["url"].endswith(".jpg")
    assert body["size_bytes"] == len(fake_jpg)
    assert body["content_type"] == "image/jpeg"

    saved = media_tmp / body["filename"]
    assert saved.exists() and saved.read_bytes() == fake_jpg


async def test_upload_image_rejects_unsupported_type(
    client: AsyncClient, admin_headers: dict[str, str], media_tmp: Path
) -> None:
    files = {"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")}
    r = await client.post("/api/v1/upload/image", headers=admin_headers, files=files)
    assert r.status_code == 415


async def test_upload_image_rejects_too_large(
    client: AsyncClient, admin_headers: dict[str, str], media_tmp: Path
) -> None:
    from app.core.config import settings

    big = b"\x00" * (settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    files = {"file": ("big.png", io.BytesIO(big), "image/png")}
    r = await client.post("/api/v1/upload/image", headers=admin_headers, files=files)
    assert r.status_code == 413


async def test_upload_image_requires_product_write(
    client: AsyncClient, sales_headers: dict[str, str], media_tmp: Path
) -> None:
    files = {"file": ("t.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")}
    r = await client.post("/api/v1/upload/image", headers=sales_headers, files=files)
    assert r.status_code == 403

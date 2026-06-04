"""Katalog uchun yordamchi funksiyalar — slug, SKU avto-generatsiya."""
from __future__ import annotations

import re
import secrets
import unicodedata


def slugify(value: str) -> str:
    """ASCII-friendly slug — kichik harf, defis bilan."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value or "item"


def _ascii_upper_alnum(value: str, limit: int) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", slugify(value)).upper()
    return (cleaned[:limit] or "X" * limit).ljust(limit, "X") if limit else cleaned


def generate_sku_prefix(name: str) -> str:
    """Mahsulot uchun globally-unique SKU prefiks. 6 belgi + 4 hex suffiks.

    Misol: "Mayka klassik" -> "MAYKAK-A3F2"
    Globally unique: tasodifiy 4 hex (16^4 = 65 536) kollizion ehtimoli juda past;
    DB darajasidagi UNIQUE(sku_prefix) yakuniy himoya beradi.
    """
    base = _ascii_upper_alnum(name, 6)
    suffix = secrets.token_hex(2).upper()  # 4 hex
    return f"{base}-{suffix}"


def build_variant_sku(prefix: str, size: str, color: str) -> str:
    """Variant SKU = `{prefix}-{SIZE}-{COL3}`.
    Prefiks unique bo'lgani uchun variant SKU ham globally unique
    (qo'shimcha ravishda (product_id,size,color) ham unique).
    """
    size_code = _ascii_upper_alnum(size, 0)[:8] or "ONE"
    color_code = _ascii_upper_alnum(color, 0)[:3] or "XXX"
    return f"{prefix}-{size_code}-{color_code}"

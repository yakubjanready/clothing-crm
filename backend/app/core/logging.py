"""Markazlashgan logging sozlamasi + maxfiy ma'lumotni redaction filter.

Maxfiy maydonlar (`password`, `token`, `secret`, ...) log yozuvlarida
`***` bilan almashtiriladi — case-insensitive, key:value yoki dict ichida.
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Iterable
from typing import Any

from app.core.config import settings

REDACTED = "***REDACTED***"


def _build_redact_pattern(fields: Iterable[str]) -> re.Pattern[str]:
    keys = "|".join(re.escape(f) for f in fields)
    # Misol formatlar: password=foo, "password": "foo", 'password': 'foo'
    pattern = rf"(?i)\b({keys})\b\s*[=:]\s*['\"]?([^'\",\s\}}]+)['\"]?"
    return re.compile(pattern)


def _redact_dict(d: dict[str, Any], fields_lower: set[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(k, str) and k.lower() in fields_lower:
            out[k] = REDACTED
        elif isinstance(v, dict):
            out[k] = _redact_dict(v, fields_lower)
        else:
            out[k] = v
    return out


class RedactFilter(logging.Filter):
    """Log record'larida maxfiy maydonlarni yashiradigan filter."""

    def __init__(self, fields: list[str]) -> None:
        super().__init__()
        self._fields = fields
        self._fields_lower = {f.lower() for f in fields}
        self._pattern = _build_redact_pattern(fields)

    def filter(self, record: logging.LogRecord) -> bool:
        # 1) record.msg (asosan format string)
        if isinstance(record.msg, str):
            record.msg = self._pattern.sub(r"\1=" + REDACTED, record.msg)
        # 2) record.args — dict yoki tuple ko'rinishida bo'lishi mumkin
        if record.args:
            if isinstance(record.args, dict):
                record.args = _redact_dict(record.args, self._fields_lower)
            elif isinstance(record.args, tuple):
                new_args: list[Any] = []
                for a in record.args:
                    if isinstance(a, dict):
                        new_args.append(_redact_dict(a, self._fields_lower))
                    elif isinstance(a, str):
                        new_args.append(self._pattern.sub(r"\1=" + REDACTED, a))
                    else:
                        new_args.append(a)
                record.args = tuple(new_args)
        return True


def setup_logging() -> None:
    """Ilova boshlanishida bir marta chaqiriladi.

    - Root logger uchun StreamHandler + standart format
    - RedactFilter har bir handler'ga biriktiriladi
    - settings.LOG_LEVEL'dan level olinadi
    """
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    # Avvalgi handler'larni tozalash (qayta chaqirilishi mumkin testlarda)
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(level)

    redact = RedactFilter(settings.LOG_REDACT_FIELDS)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    handler.addFilter(redact)
    root.addHandler(handler)

    # Uvicorn loggerlariga ham qo'llanish
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.addFilter(redact)
        lg.propagate = True

    # SQLAlchemy echo (DEBUG)'da ham parol DB URL'da bo'lishi mumkin
    logging.getLogger("sqlalchemy.engine").addFilter(redact)

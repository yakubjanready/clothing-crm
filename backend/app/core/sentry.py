"""Sentry SDK init — agar SENTRY_DSN o'rnatilgan bo'lsa.
DSN bo'sh bo'lsa, init bo'lmaydi (dev/test'da overhead yo'q)."""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry() -> bool:
    """True qaytaradi agar Sentry init qilingan bo'lsa, aks holda False."""
    if not settings.SENTRY_DSN:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            release=__import__("app").__version__,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                CeleryIntegration(),
            ],
            send_default_pii=False,
        )
        logger.info("Sentry initialized for env=%s", settings.APP_ENV)
        return True
    except Exception:
        logger.exception("Sentry init failed — davom etamiz Sentry'siz")
        return False

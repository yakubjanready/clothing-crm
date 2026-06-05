import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import close_redis
from app.core.sentry import init_sentry
from app.db.session import dispose_engine

# Logging + Sentry init create_app'dan oldin —
# Integrationlar future request'larni ushlab olishi uchun.
setup_logging()
init_sentry()


API_DESCRIPTION = """
**Ulgurji Kiyim-kechak CRM** — ulgurji savdo kompaniyasi uchun to'liq CRM tizimi.

### Modullar
- 🔐 **Auth + RBAC** — JWT (access+refresh rotation), 7 ta rol, 24 ruxsat
- 👥 **HR** — bo'limlar, lavozimlar, xodimlar (audit-log)
- 📦 **Katalog** — kategoriya daraxti, brand, mahsulot+variant (rasm yuklash)
- 🏪 **Ombor** — `Warehouse`, `Stock` (reserve/release), `StockMovement`, inventarizatsiya
- 🤝 **Mijozlar** — segment, kredit limit, kontaktlar, o'zaro aloqalar
- 💵 **Sotuv** — buyurtma (state machine), to'lov, schyot-faktura, qaytarish
- 🚚 **Ta'minot** — yetkazib beruvchilar, sotib olish buyurtmalari
- 💰 **Moliya** — hisoblar, daromad/xarajat, qarz ledgeri
- 🔔 **Bildirishnomalar** — WebSocket (JWT auth) + REST

### Xavfsizlik
- Login brute-force lockout: 5 ta xato → 15 daqiqa
- Audit log: barcha auth + kritik amallar (`/api/v1/hr/audit-logs`)
- Maxfiy maydonlar log'da yashirin (`***REDACTED***`)
"""


def _tags_metadata() -> list[dict[str, str]]:
    return [
        {"name": "health", "description": "Liveness va versiya tekshiruvi."},
        {"name": "auth", "description": "Autentifikatsiya: login, refresh, logout, me, register."},
        {"name": "hr", "description": "HR modul: bo'limlar, lavozimlar, xodimlar, audit-log."},
        {
            "name": "catalog",
            "description": "Mahsulot katalogi: kategoriya, brand, mahsulot, variant.",
        },
        {"name": "warehouse", "description": "Ombor: stock, movement, inventarizatsiya."},
        {"name": "customers", "description": "Mijozlar: profil, kontaktlar, kredit limit."},
        {"name": "sales", "description": "Sotuv: buyurtma, to'lov, invoice, qaytarish."},
        {"name": "procurement", "description": "Ta'minot: supplier, purchase order."},
        {"name": "finance", "description": "Moliya: hisoblar, to'lovlar, qarz ledgeri."},
        {"name": "notifications", "description": "Bildirishnomalar: WebSocket + REST."},
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await dispose_engine()
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ulgurji Kiyim-kechak CRM API",
        description=API_DESCRIPTION,
        version=__version__,
        debug=settings.DEBUG,
        lifespan=lifespan,
        contact={"name": "CRM dev", "email": "softweydev@gmail.com"},
        license_info={"name": "Proprietary"},
        openapi_tags=_tags_metadata(),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "env": settings.APP_ENV,
            "version": __version__,
        }

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    app.mount(
        settings.MEDIA_URL_PREFIX,
        StaticFiles(directory=settings.MEDIA_ROOT),
        name="media",
    )

    return app


app = create_app()

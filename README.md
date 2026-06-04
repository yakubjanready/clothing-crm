# Ulgurji Kiyim-kechak CRM

Ulgurji kiyim-kechak kompaniyasi uchun CRM tizimi. BTEC networking/infrastructure topshirig'i doirasida bosqichma-bosqich (faza N) yetkazib beriladi.

## Stek

- **Backend**: FastAPI · PostgreSQL · Redis · SQLAlchemy (async) · Alembic · Celery
- **Frontend**: React + TypeScript · Vite · TailwindCSS · shadcn/ui
- **Infra**: Docker · docker-compose · GitLab CI/CD · Hetzner (SSH)

## Monorepo tuzilmasi

```
clothing-crm/
├── backend/                 FastAPI ilova
│   ├── app/
│   │   ├── api/v1/          REST endpointlar
│   │   ├── core/            sozlamalar, xavfsizlik
│   │   ├── db/              SQLAlchemy session/base
│   │   ├── models/          ORM modellar
│   │   ├── schemas/         Pydantic sxemalar
│   │   ├── services/        biznes-logika
│   │   ├── tasks/           Celery vazifalar
│   │   ├── utils/           yordamchilar
│   │   └── main.py          FastAPI entrypoint
│   ├── alembic/             migratsiyalar
│   ├── tests/               pytest
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example
├── frontend/                React + TS + Vite
│   ├── src/
│   ├── package.json
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml
├── screenshots/             BTEC dalillar (manifest.md)
└── README.md
```

## Tezkor ishga tushirish

```bash
# .env tayyorlash
cp backend/.env.example  backend/.env
cp frontend/.env.example frontend/.env

# Hammasini ko'tarish
docker compose up --build
```

Endpointlar:
- Backend health: http://localhost:8000/health
- Frontend:       http://localhost:5173
- API docs:       http://localhost:8000/docs

## Lokal (Docker'siz)

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
pytest
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
npm run test
```

## Ma'lumotlar bazasi va migratsiyalar

Loyiha **PostgreSQL** (async, `asyncpg` drayveri) va **Alembic** dan foydalanadi.

### Umumiy mixinlar (`backend/app/db/base.py`)

Har bir biznes modeli quyidagi mixinlardan meros oladi:
- `UUIDPrimaryKeyMixin` — `id: UUID` (default `uuid4`)
- `TimestampMixin` — `created_at`, `updated_at` (TZ-aware, server-side `NOW()`)
- `SoftDeleteMixin` — `deleted_at` (nullable), `is_deleted`, `soft_delete()`, `restore()`

Misol:
```python
from app.db import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin

class Customer(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "customers"
    # ... ustunlar
```

### Alembic buyruqlari

**Yangi model qo'shgandan keyin** (`app/models/<name>.py` faylida) — modelni
`app/models/__init__.py` orqali import qilib, autogenerate ishlatish:

```bash
# Docker bilan (compose ishga tushgan paytda):
docker compose exec backend alembic revision --autogenerate -m "add customers"
docker compose exec backend alembic upgrade head

# Lokal venv'da:
cd backend
alembic revision --autogenerate -m "add customers"
alembic upgrade head
```

**Boshqa foydali buyruqlar:**
```bash
alembic current              # joriy versiyani ko'rsatish
alembic history --verbose    # to'liq tarix
alembic downgrade -1         # bitta orqaga qaytarish
alembic downgrade base       # boshlang'ich holatga qaytarish
alembic upgrade head --sql   # SQL chiqarish (DBga tegmasdan, prod review uchun)
```

**Eslatma:** alembic autogenerate'ning ishlashi uchun barcha modellar
`alembic/env.py`'da ko'rinadigan bo'lishi kerak (`import app.models`).
Hozircha biznes modellar yo'q — bo'sh placeholder qoldirilgan.

## Faza intizomi

Har bir faza yakuni: **TEST → SCREENSHOT → COMMIT → "FAZA N TUGADI"**.
Tafsilot: `screenshots/manifest.md`.

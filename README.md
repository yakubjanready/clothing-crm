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

## CI/CD pipeline (GitLab) — BTEC D.P8

Loyiha **GitLab CI/CD** orqali avtomatlashtirilgan: har commit'da kod sifati
tekshiriladi, testlar yuritiladi, `main`/`master` branch'da Docker image'lar
qurilib Container Registry'ga push qilinadi va qo'lda tasdiqlashdan keyin
Hetzner serverga deploy bo'ladi.

### Bosqichlar (`.gitlab-ci.yml`)

```
┌───────┐   ┌───────┐   ┌───────────────┐   ┌─────────────────┐
│ lint  │ → │ test  │ → │ build (main)  │ → │ deploy (manual) │
└───────┘   └───────┘   └───────────────┘   └─────────────────┘
   │           │              │                     │
   ├ backend   ├ pytest       ├ backend image       ├ rsync compose+nginx
   │ ruff      │ + postgres   │ → registry          ├ ssh: pull + up -d
   │ black     │ + redis      │ (sha + latest)      ├ alembic upgrade head
   │ mypy      │              ├ frontend image      └ image prune
   └ frontend  └ vitest       └ → registry
     eslint      + build
     prettier
```

| Stage | Job | Image | Cache | Maqsad |
|-------|-----|-------|-------|--------|
| lint    | `backend:lint`   | python:3.12-slim | pip   | `ruff` + `black --check` + `mypy` |
| lint    | `frontend:lint`  | node:20-alpine   | npm   | `npm run lint` + `format:check` |
| test    | `backend:test`   | python:3.12-slim | pip   | `pytest --cov-fail-under=80` (services: postgres:16, redis:7) |
| test    | `frontend:test`  | node:20-alpine   | npm   | `vitest run` + `vite build` |
| build   | `build:backend`  | docker:27 (dind) | —     | `$CI_REGISTRY_IMAGE/backend:$SHA` + `:latest` (faqat main) |
| build   | `build:frontend` | docker:27 (dind) | —     | `$CI_REGISTRY_IMAGE/frontend:$SHA` + `:latest` (faqat main) |
| deploy  | `deploy:prod`    | alpine:3.20      | —     | SSH (Hetzner) → `docker compose pull/up -d` → `alembic upgrade head` (manual) |

### Talab qilinadigan CI/CD Variables

GitLab'da: **Settings → CI/CD → Variables**. Hammasi `Masked` va `Protected`
bo'lishi kerak (deploy faqat `main`/`master`'da bajariladi).

| Variable | Tur | Tavsif |
|----------|------|--------|
| `SSH_PRIVATE_KEY`    | File   | Hetzner `deploy@$SERVER_IP` foydalanuvchisi uchun maxfiy SSH kalit (PEM). Server `~/.ssh/authorized_keys`'ga mos `.pub` qo'shilgan bo'lishi shart. |
| `SERVER_IP`          | Var    | Hetzner IP yoki DNS (masalan `5.75.xxx.xxx` yoki `crm.example.uz`). |
| `DB_PASSWORD`        | Masked | PostgreSQL parol (test + prod). |
| `JWT_SECRET`         | Masked | `SECRET_KEY` (≥32 belgi). Test stage va prod uchun. |
| `VITE_API_BASE_URL`  | Var    | Ixtiyoriy. Bo'sh qoldirilsa nginx reverse proxy ishlatiladi (`/api/...`). |
| `VITE_SENTRY_DSN`    | Masked | Ixtiyoriy. Frontend Sentry DSN (`@sentry/react`). |
| `CI_REGISTRY_*`      | Auto   | GitLab tomonidan avtomatik: `CI_REGISTRY`, `CI_REGISTRY_USER`, `CI_REGISTRY_PASSWORD`, `CI_REGISTRY_IMAGE`. Qo'shimcha registry token shart emas. |

### Server (Hetzner) tayyorgarligi (bir martalik)

```bash
# Server'da:
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy
sudo mkdir -p /opt/crm && sudo chown deploy:deploy /opt/crm

# Local'dan kalitni o'rnatish:
ssh-copy-id -i ~/.ssh/crm_deploy.pub deploy@$SERVER_IP

# Server'da .env.prod ni tayyorlash:
ssh deploy@$SERVER_IP "cd /opt/crm && nano .env.prod"   # .env.prod.example asosida

# Bir martalik bootstrap (registry login + birinchi seed):
ssh deploy@$SERVER_IP "
  cd /opt/crm &&
  docker login registry.gitlab.com &&
  docker compose -f docker-compose.prod.yml --env-file .env.prod up -d &&
  docker compose -f docker-compose.prod.yml exec backend python -m app.scripts.seed_rbac
"
```

### Lokal'da pipeline'ni simulyatsiya qilish

```bash
# YAML sintaksisi (gitlab-ci-local — npm paketi):
npx --yes gitlab-ci-local --list

# Bitta jobni lokal'da bajarish:
npx --yes gitlab-ci-local backend:lint
```

## Faza intizomi

Har bir faza yakuni: **TEST → SCREENSHOT → COMMIT → "FAZA N TUGADI"**.
Tafsilot: `screenshots/manifest.md`.

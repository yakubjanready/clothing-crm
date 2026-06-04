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

## Faza intizomi

Har bir faza yakuni: **TEST → SCREENSHOT → COMMIT → "FAZA N TUGADI"**.
Tafsilot: `screenshots/manifest.md`.

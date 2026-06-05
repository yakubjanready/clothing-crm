# ----------------------------------------------------------------------------
# Backend prod image — multi-stage, non-root, gunicorn + UvicornWorker.
# ----------------------------------------------------------------------------

# ---- Stage 1: builder ----
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# Avval faqat metadatani ko'chirib, deps'ni o'rnatamiz (Docker layer cache).
COPY pyproject.toml ./
COPY app ./app

# `--user` bilan ~/.local ga o'rnatadi — keyin runtime stage'iga ko'chiramiz.
RUN pip install --upgrade pip \
 && pip install --user --no-warn-script-location .

# ---- Stage 2: runtime ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/app/.local/bin:$PATH \
    PYTHONPATH=/app

# curl healthcheck uchun; libpq, libssl asyncpg/cryptography uchun runtime sifatida kerak emas
# (asyncpg pure-python crypto bilan ishlaydi; sqlalchemy ham tarmoq orqali).
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1000 app \
 && useradd  --system --uid 1000 --gid app --create-home --home-dir /home/app app

WORKDIR /app

# Builderdagi ~/.local ni runtime userning home'iga ko'chiramiz.
COPY --from=builder --chown=app:app /root/.local /home/app/.local

# Ilova kodi
COPY --chown=app:app app    ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini ./alembic.ini
COPY --chown=app:app pyproject.toml ./pyproject.toml

# media papkasi (volume mount nuqta)
RUN mkdir -p /app/media && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

# gunicorn + UvicornWorker — prod uchun standart shaklda.
# WEB_CONCURRENCY env bilan worker sonini boshqarish mumkin (default: 2).
CMD ["sh", "-c", "exec gunicorn app.main:app \
    --workers ${WEB_CONCURRENCY:-2} \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 60 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile - \
    --log-level ${LOG_LEVEL:-info}"]

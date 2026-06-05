# Ulgurji Kiyim-kechak CRM — root Makefile
# Linux/macOS: `make <target>`. Windows: `make` o'rniga PowerShell skript bilan
# yoki Git Bash orqali ishlatiladi.
#
# Asosiy target'lar:
#   make install        — backend + frontend bog'liqliklarini o'rnatish
#   make lint           — ruff + black --check + eslint + prettier --check
#   make format         — ruff format + black + prettier --write
#   make typecheck      — mypy (backend) + tsc --noEmit (frontend)
#   make test           — pytest + vitest
#   make test-cov       — coverage hisobot bilan
#   make precommit      — pre-commit barcha hook'larni ishga tushirish
#   make up / down      — docker compose
#   make migrate / seed — alembic upgrade head + RBAC seed
#   make ci             — lint + typecheck + test-cov (CI'da ishlatish)

SHELL := /bin/bash

BACKEND := backend
FRONTEND := frontend
PY := $(BACKEND)/.venv/Scripts/python.exe
ifeq ($(OS),Windows_NT)
PY := $(BACKEND)/.venv/Scripts/python.exe
else
PY := $(BACKEND)/.venv/bin/python
endif

.PHONY: help install install-backend install-frontend \
        lint lint-backend lint-frontend \
        format format-backend format-frontend \
        typecheck typecheck-backend typecheck-frontend \
        test test-backend test-frontend test-cov test-cov-backend test-cov-frontend \
        precommit precommit-install \
        up down logs migrate seed \
        clean ci

help:  ## Mavjud target'larni ko'rsatadi
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---------- install ----------

install: install-backend install-frontend  ## Backend + frontend bog'liqliklarini o'rnatish

install-backend:  ## Backend deps (dev)
	cd $(BACKEND) && $(PY) -m pip install -e ".[dev]"

install-frontend:  ## Frontend deps
	cd $(FRONTEND) && npm install --legacy-peer-deps

# ---------- lint ----------

lint: lint-backend lint-frontend  ## Barcha linterlar (ruff + black + eslint + prettier --check)

lint-backend:
	cd $(BACKEND) && $(PY) -m ruff check app tests
	cd $(BACKEND) && $(PY) -m black --check app tests

lint-frontend:
	cd $(FRONTEND) && npm run lint
	cd $(FRONTEND) && npm run format:check

# ---------- format ----------

format: format-backend format-frontend  ## Auto-format barcha kod

format-backend:
	cd $(BACKEND) && $(PY) -m ruff check --fix app tests
	cd $(BACKEND) && $(PY) -m ruff format app tests
	cd $(BACKEND) && $(PY) -m black app tests

format-frontend:
	cd $(FRONTEND) && npm run lint:fix
	cd $(FRONTEND) && npm run format

# ---------- typecheck ----------

typecheck: typecheck-backend typecheck-frontend  ## mypy + tsc

typecheck-backend:
	cd $(BACKEND) && $(PY) -m mypy app

typecheck-frontend:
	cd $(FRONTEND) && npm run typecheck

# ---------- test ----------

test: test-backend test-frontend  ## Barcha testlar

test-backend:
	cd $(BACKEND) && $(PY) -m pytest

test-frontend:
	cd $(FRONTEND) && npm test

test-cov: test-cov-backend test-cov-frontend  ## Coverage hisobot bilan

test-cov-backend:
	cd $(BACKEND) && $(PY) -m pytest --cov=app --cov-report=term --cov-report=html

test-cov-frontend:
	cd $(FRONTEND) && npm run test:cov

# ---------- pre-commit ----------

precommit-install:  ## Pre-commit hook'larini lokalga o'rnatish
	pre-commit install

precommit:  ## Barcha hook'larni hozir ishga tushirish
	pre-commit run --all-files

# ---------- docker ----------

up:  ## docker compose up (postgres + redis + backend + celery + frontend)
	docker compose up -d --build

down:  ## docker compose down (volumelar saqlanadi)
	docker compose down

logs:
	docker compose logs -f --tail=100

# ---------- alembic + seed ----------

migrate:  ## alembic upgrade head (lokal venv)
	cd $(BACKEND) && $(PY) -m alembic upgrade head

migrate-docker:  ## alembic upgrade head (docker)
	docker compose exec backend alembic upgrade head

seed:  ## RBAC seed (lokal)
	cd $(BACKEND) && $(PY) -m app.scripts.seed_rbac

seed-docker:
	docker compose exec backend python -m app.scripts.seed_rbac

# ---------- misc ----------

clean:  ## Kesh va build artefaktlarini tozalash
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/htmlcov $(BACKEND)/.coverage
	rm -rf $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache
	rm -rf $(FRONTEND)/dist $(FRONTEND)/coverage $(FRONTEND)/.vite

ci: lint typecheck test-cov  ## CI quvuri uchun (lint + types + coverage)

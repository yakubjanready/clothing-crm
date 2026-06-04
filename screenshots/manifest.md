# Screenshots Manifest

Har bir fazada to'plangan dalillar ro'yxati. Nomlash:
`<BTEC-criteria>__<phase>__<order>-<short-desc>.png`
(agar mezon yo'q bo'lsa: `setup__<phase>__<order>-...png`).

**Maxfiy ma'lumotlar** (parol, token, IP, SSH kalit) skrinshot olishdan oldin yashirilishi/blur qilinishi shart.

## Faza 1 — Skelet

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| setup__faza1__01-tree.png            | 1 | setup | Loyiha katalog tuzilmasi (monorepo) |
| setup__faza1__02-pytest-green.png    | 1 | setup | Backend pytest yashil — /health testi |
| setup__faza1__03-vitest-green.png    | 1 | setup | Frontend vitest yashil — smoke test |
| setup__faza1__04-git-push.png        | 1 | setup | GitLab'ga push muvaffaqiyatli |

## Faza 2 — DB qatlami (mixinlar + Alembic async)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| db__faza2__01-pytest-green.png       | 2 | db | Backend pytest yashil — 9 ta test (test_db_base.py qo'shildi) |
| db__faza2__02-db-layer-loaded.png    | 2 | db | DB qatlami import + Alembic config yuklanishi (engine: postgresql+asyncpg) |

## Faza 3 — Auth + RBAC

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| auth__faza3__01-pytest-green.png     | 3 | auth | 38 ta test yashil (security 10, modellar 6, endpointlar 13 — aiosqlite + fakeredis) |
| auth__faza3__02-alembic-migration.png| 3 | auth | Alembic autogenerate + upgrade head: permissions, roles, users, user_roles, role_permissions |
| auth__faza3__03-seed-rbac.png        | 3 | auth | Real Postgres'da seed: 15 perm + 7 rol + 47 role-perm mapping + admin user |

## Faza 4 — HR moduli (Department/Position/Employee + audit)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| hr__faza4__01-pytest-green.png       | 4 | hr | 57 ta test yashil (pagination 5, HR CRUD 14, mavjudlar 38) |
| hr__faza4__02-alembic-migrations.png | 4 | hr | Alembic: auth_rbac → hr_module migratsiya; tarix va current |
| hr__faza4__03-db-tables.png          | 4 | hr | Real Postgres: 10 jadval, 19 perm (4 yangi: hr:read/write/delete + audit:read), 55 role-perm mapping |

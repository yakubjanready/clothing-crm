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

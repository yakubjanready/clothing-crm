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

## Faza 5 — Katalog (Category/Brand/Product/Variant + upload)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| catalog__faza5__01-pytest-green.png       | 5 | catalog | 76 ta test yashil (catalog 19: slugify+SKU pure 4, category tree 3, brand 1, product filter 2, variant single+matrix+unique 4, upload 4, permission 1) |
| catalog__faza5__02-alembic-migrations.png | 5 | catalog | Alembic: hr_module → catalog_module; categories/brands/products/product_variants/attribute_values |
| catalog__faza5__03-db-tables.png          | 5 | catalog | Real Postgres: 15 jadval (5 yangi), 20 perm (product:delete qo'shildi) |

## Faza 6 — Ombor (Warehouse/Stock/StockMovement/Inventory)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| warehouse__faza6__01-pytest-green.png       | 6 | warehouse | 94 ta test yashil (warehouse 18: CRUD 4, receive/issue 3, transfer atomik 3, reserve/release 4, low-stock notify celery 1, inventory finalize 2, history 1) |
| warehouse__faza6__02-alembic-migrations.png | 6 | warehouse | Alembic: catalog_module → warehouse_module; warehouses/stocks (CHECK)/stock_movements/inventories/inventory_items |
| warehouse__faza6__03-db-tables.png          | 6 | warehouse | Real Postgres: 20 jadval, stocks ko'p CHECK constraintlari + UNIQUE(warehouse_id, variant_id) |

## Faza 7 — Mijozlar (Customer/Contact/Interaction + kredit limit)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| customer__faza7__01-pytest-green.png       | 7 | customer | 112 ta test yashil (customer 18: kredit limit pure 6, CRUD+filter 6, contacts 2, interactions 2, balance 2) |
| customer__faza7__02-alembic-migrations.png | 7 | customer | Alembic: warehouse_module → customer_module; customers (CHECK debt/credit_limit>=0)/customer_contacts/customer_interactions |
| customer__faza7__03-db-tables.png          | 7 | customer | Real Postgres: 23 jadval, 21 perm (customer:delete qo'shildi), customers CHECK va CASCADE FK lar |

## Faza 8 — Sotuv (Order/OrderItem/Payment/Invoice/Return + state machine + Celery PDF)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| sales__faza8__01-pytest-green.png       | 8 | sales | 152 ta test yashil (sales 40: state machine pure 14, create draft+confirm+pay+ship+cancel+return+invoice e2e) |
| sales__faza8__02-alembic-migrations.png | 8 | sales | Alembic: customer → sales_module; orders/order_items/payments/invoices/returns/return_items |
| sales__faza8__03-db-tables.png          | 8 | sales | Real Postgres: 29 jadval, orders CHECK constraintlari + CASCADE FK (items/payments/invoices) va RESTRICT (returns, customer, warehouse) |

## Faza 9 — Ta'minot (Supplier/PurchaseOrder/PurchaseItem/SupplierPayment)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| procurement__faza9__01-pytest-green.png       | 9 | procurement | 174 ta test yashil (procurement 22: state machine 7, supplier CRUD 4, PO create+receive (stock+cost+debt) 4, pay 4, cancel+balance 3) |
| procurement__faza9__02-alembic-migrations.png | 9 | procurement | Alembic: sales → procurement_module; suppliers/purchase_orders/purchase_items/supplier_payments + ProductVariant.cost_price ustuni |
| procurement__faza9__03-db-tables.png          | 9 | procurement | Real Postgres: 33 jadval, suppliers CHECK (debt>=0, rating 0-5), product_variants.cost_price ustuni qo'shildi |

## Faza 10 — Moliya (Account/FinancePayment/DebtRecord)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| finance__faza10__01-pytest-green.png       | 10 | finance | 190 ta test yashil (finance 16: account CRUD 5, income/expense+insufficient 4, transfer atomik 3, debts auto-write 3, list filter 1) |
| finance__faza10__02-alembic-migrations.png | 10 | finance | Alembic: procurement → finance_module; accounts/finance_payments/debt_records |
| finance__faza10__03-db-tables.png          | 10 | finance | Real Postgres: 36 jadval, accounts CHECK (balance>=0), finance_payments CHECK (amount>0), debt_records ledger jadvali |

## Faza 11 — Notifikatsiyalar (Notification + WebSocket + Redis Pub/Sub)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| notify__faza11__01-pytest-green.png       | 11 | notification | 202 ta test yashil (notification 12: notify() service 3, WS auth 3, REST 5, auto-trigger 1) |
| notify__faza11__02-alembic-migrations.png | 11 | notification | Alembic: finance → notifications; user_id FK CASCADE |
| notify__faza11__03-db-tables.png          | 11 | notification | Real Postgres: 37 jadval, notifications table (type/severity index, read_at index, data JSON) |

## Faza 12 — Frontend skelet (React+TS+Vite+Tailwind+shadcn+Router+Query+Zustand+i18n+theme)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| frontend__faza12__01-vitest-green.png  | 12 | frontend | 6 ta vitest yashil (App: 2, auth store: 4) — login form, ProtectedRoute redirect, Zustand login/logout/hasRole |
| frontend__faza12__02-build-success.png | 12 | frontend | TypeScript build + Vite bundle muvaffaqiyatli (1832 modul, ~505KB JS gzipped 159KB, ~17KB CSS) |
| frontend__faza12__03-tree.png          | 12 | frontend | 39 ta fayl: lib (api+i18n+utils), stores (auth+test), components (ui/8 + layout/5 + common/6 + auth + theme), pages (5), locales (uz/ru/en) |

## Faza 13 — Mahsulotlar UI (list+filter+pagination, create/edit RHF+Zod, detail+variants+drag-drop)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| products_ui__faza13__01-vitest-green.png  | 13 | products_ui | 11 ta vitest yashil (App: 2, auth: 4, product-schema Zod: 5) |
| products_ui__faza13__02-build-success.png | 13 | products_ui | Vite build: 1887 modul, 718KB JS (gzip 219KB), 22KB CSS |
| products_ui__faza13__03-tree.png          | 13 | products_ui | Yangi UI fayllari: api/{catalog,products,types}, pages/catalog/{List,Detail,Create,Edit,Form,Dropzone,MatrixDialog}, ui/{dialog,select,badge,textarea,form}, common/{Pagination,SearchInput,ConfirmDialog} |

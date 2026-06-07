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

## Faza 14 — Quality (coverage >80%, ruff+black+mypy, ESLint+Prettier, pre-commit, Makefile)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| quality__faza14__01-backend-coverage.png | 14 | quality | Backend coverage 80.7% (fail_under=80), 214 ta test yashil (asosiy logika: services 78-100%, schemas 100%, utils 100%) |
| quality__faza14__02-backend-lint.png     | 14 | quality | ruff check (187 ta xato fix'landi) va black --check yashil |
| quality__faza14__03-frontend-test.png    | 14 | quality | Frontend vitest (11 passed) + @vitest/coverage-v8 sozlanildi (stores 96.55%, schemas 100%, lib 100%) |
| quality__faza14__04-frontend-lint.png    | 14 | quality | ESLint (typescript-eslint + react + react-hooks, flat config) va Prettier --check yashil |

## Faza 15 — Production infra (Docker prod + Nginx + compose + Sentry + DB backup)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| prod__faza15__01-compose-config.png      | 15 | prod_infra | docker-compose.prod.yml — 8 ta xizmat (postgres+volume, redis, backend, celery_worker, celery_beat, frontend, nginx, minio) syntax+env validate |
| prod__faza15__02-backend-image-build.png | 15 | prod_infra | Backend multi-stage build success: 245MB, non-root uid 1000 (app), gunicorn /home/app/.local/bin, Python 3.12 |
| prod__faza15__03-nginx-validate.png      | 15 | prod_infra | Reverse proxy `nginx -t` syntax OK (locations: /api/, /api/v1/auth/(login\|refresh), /ws/, /media/, /; gzip, security headers, rate limit) |

## Faza 16 — CI/CD (GitLab pipeline: lint → test → build → deploy, BTEC D.P8)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| cicd__faza16__01-ci-yaml-validate.png | 16 | D.P8 | `.gitlab-ci.yml` YAML syntax OK — 4 stage, 7 job (backend/frontend × lint/test/build + deploy:prod), 4 hidden template (.python .node .docker .main-only) |
| cicd__faza16__02-stages-overview.png  | 16 | D.P8 | Pipeline strukturasi: `stage`, `image`, `services`, `extends`, `needs`, `rules`, `coverage`, `environment` qatorlari ko'rinadi |
| cicd__faza16__03-cicd-variables.png   | 16 | D.P8 | GitLab CI/CD Variables ro'yxati: SSH_PRIVATE_KEY (File, Masked, Protected), SERVER_IP, DB_PASSWORD, JWT_SECRET, VITE_API_BASE_URL, VITE_SENTRY_DSN + GitLab auto registry vars |
| cicd__faza16__04-deploy-flow.png      | 16 | D.P8 | Build → deploy oqimi: registry push, rsync compose+nginx, SSH `docker login` + `pull` + `up -d --no-build` + `alembic upgrade head` + `image prune` |

## Faza 17 — Hetzner Cloud production deploy (real infra, BTEC M.P3/D.M2)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| cloud__faza17__01-hcloud-resources.png    | 17 | infra_iac | `hcloud {ssh-key,network,firewall,server} list` — yaratilgan resurslar: SSH key `crm-deploy` (113351723), Network `crm-vpc` 10.0.0.0/16 (12303662), Firewall `crm-fw` 4 qoida (11086775), Server `crm-app-01` CPX22 nbg1 138.199.218.108 (136912192) |
| cloud__faza17__02-ssh-bootstrap.png       | 17 | infra_iac | SSH ulanish + cloud-init holati: hostname crm-app-01 x86_64, Docker 29.5.3, compose v5.1.4, UFW active (22/80/443), systemd: docker+netdata+fail2ban active, `/var/log/crm-bootstrap.log` |
| cloud__faza17__03-stack-running.png       | 17 | prod_deploy | 8 ta Docker xizmat `Up (healthy)` (postgres, redis, backend, celery_worker, celery_beat, frontend, nginx, minio); tashqi smoke test 138.199.218.108: /healthz=ok, /=200, /docs=200 |
| cloud__faza17__04-db-migrations.png       | 17 | prod_deploy | Alembic current: c1e9c4b3fdcb (notifications, eng oxirgi); history 12 ta migratsiya (auth_rbac→hr→catalog→warehouse→customer→sales→procurement→finance→notifications); PostgreSQL: 37 ta jadval |
| cloud__faza17__05-monitoring-security.png | 17 | observability | Netdata v2.10.3 active+listening :19999 (Hetzner FW'da bloklangan, SSH tunnel only); sshd: PermitRootLogin=no, PasswordAuthentication=no, MaxAuthTries=3; fail2ban sshd jail active |

## Faza 18 — CI/CD avtomatik deploy (GitLab pipeline → Hetzner, BTEC D.P8 yakuni)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| cicd_deploy__faza18__01-deploy-result.png | 18 | D.P8 | CI/CD deploy passed: serverdagi backend/celery_worker/celery_beat/frontend image'lari `registry.gitlab.com/.../backend:64d593a2` va `.../frontend:64d593a2` (avval lokal `crm-backend:prod` edi); /healthz=ok, /=200, /docs=200; alembic head c1e9c4b3fdcb |
| cicd_deploy__faza18__02-pipeline-fix.png  | 18 | D.P8 | Pipeline #2579385458 deploy:prod libcrypto error tuzatish: GitLab File-tipidagi $SSH_PRIVATE_KEY fayl yo'lini beradi → `ssh-add "$SSH_PRIVATE_KEY"` (echo+pipe o'rniga); Hetzner firewall 22→0.0.0.0/0 (kalit-only + fail2ban himoyalaydi) |

## Faza 19 — Xavfsizlik + audit + optimizatsiya + hujjatlar (BTEC B.M2/D.M4 yakuni)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| sec__faza19__01-brute-force-tests.png    | 19 | security | 15/15 auth testi yashil + 2 ta yangi (test_login_brute_force_lockout, test_login_success_resets_counter); jami 216 ta backend test passed |
| sec__faza19__02-explain-before-after.png | 19 | B.M2/D.M4 | PostgreSQL EXPLAIN ANALYZE oldin/keyin: cost 13.29→0.01 (-99.92%), planning 3.24→1.58ms (-51%), execution 0.145→0.080ms (-45%); /healthz throughput 3892→6399 req/s (+64%) |
| sec__faza19__03-security-headers.png     | 19 | security | Live tekshiruv (http://138.199.218.108): X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, CSP, Referrer-Policy, Permissions-Policy headers; nginx rate_limit zonalari |
| sec__faza19__04-audit-log-flow.png       | 19 | audit | Audit log oqim: login (success/failed)/logout har biri activity_logs jadvalga IP, action, entity_id, changes JSON bilan yoziladi; Redis brute-force lockout (5 fail → 15 daq) |
| sec__faza19__05-faza19-summary.png       | 19 | security+B.M2/D.M4 | Faza 19 to'liq yakuni: 10 ta xavfsizlik elementi, 5 ta optimizatsiya o'lchovi, 5 ta hujjat (README, BENCHMARKS, ROADMAP, DEPLOY, /docs) |

## Faza 20 — Foydalanuvchilar bo'limi (Users + Roles, BTEC C.M3)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| users__faza20__01-pytest-green.png    | 20 | users | 19/19 backend test yashil: list (5 ta — search, role/active filter, permission), get (2), patch (6 — name/roles/audit + self-block), delete/restore (2), reset-password (2), roles/me-permissions (2) |
| users__faza20__02-vitest-green.png    | 20 | users | 10/10 frontend zod test: userCreateSchema (email/parol≥8/full_name/role_ids), userEditSchema (is_active boolean), passwordResetSchema |
| users__faza20__03-endpoints.png       | 20 | users | Yangi REST routelar: GET/PATCH/DELETE /users, /restore, /reset-password, /me/permissions + GET /roles (permission_codes bilan) |
| users__faza20__04-frontend-tree.png   | 20 | users | Frontend struktura: src/pages/users/* (List/Create/Edit/Form/RolesMultiSelect + schema testi), src/api/users.ts, types.ts'ga AppUser+Role qo'shildi |
| users__faza20__05-build-success.png   | 20 | users | Vite production build muvaffaqiyatli — 2119 ta modul, 734 KB → 222 KB gzip; foydalanuvchilar sahifalari TS strict mode'da o'tdi |

## Faza 21 — Rol-asoslangan UI yashirish (sidebar + route gating, BTEC C.M3)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| rbac__faza21__01-vitest-green.png       | 21 | rbac_ui | 32/32 frontend test yashil; jumladan 8 ta yangi nav-items testi (warehouse-only/sales/hr/admin/no-perms) + 7 ta auth store testi (hasPermission, hasAnyPermission, logout reset) |
| rbac__faza21__02-permissions-matrix.png | 21 | rbac_ui | Rol bo'yicha sidebar matritsasi: warehouse-only user faqat Dashboard + Warehouse ko'radi; sales user — Customers + Sales; hr user — HR; admin — barchasi (9 modul) |
| rbac__faza21__03-arch.png               | 21 | rbac_ui | Implementation: auth store'da permissionCodes, PermissionGate komponenti, nav-items.requires + filterNav, login oqimida /auth/me + /users/me/permissions parallel chaqiruv |
| rbac__faza21__04-build-success.png      | 21 | rbac_ui | Vite production build — 737 KB → 223 KB gzip; PermissionGate + filterNav qo'shilgani holda TS strict, ESLint, Prettier — barchasi toza |

## Faza 22 — Domen (negative.uz) + Let's Encrypt TLS (BTEC M.P3 yakuni)

| Fayl | Faza | BTEC mezon | Izoh |
|------|------|------------|------|
| domain__faza22__01-arch.png            | 22 | tls_domain | DNS yo'nalish (A negative.uz/www -> 138.199.218.108); nginx 4 server bloki (80 default+ACME, 80 redirect, 443 www->apex, 443 main); docker-compose'ga certbot xizmati + 2 ta volume; init-letsencrypt.sh oqimi (dummy cert -> nginx -> certbot -> reload); HSTS+CSP qo'shildi |
| domain__faza22__02-files-and-tests.png | 22 | tls_domain | O'zgargan fayllar: nginx.conf, docker-compose.prod.yml, scripts/init-letsencrypt.sh, .env.prod, .env.prod.example, .gitlab-ci.yml, DEPLOY.md; volumelar: crm_certbot_certs (live certs + dhparam), crm_certbot_webroot (HTTP-01 challenge) |
| domain__faza22__03-tests-green.png     | 22 | tls_domain | Regressiya yo'q: 235/235 backend pytest + 32/32 frontend vitest yashil; ESLint+Prettier+ruff+black+mypy — barchasi toza |

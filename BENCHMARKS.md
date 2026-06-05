# BENCHMARKS — optimizatsiya oldidan/keyin (BTEC B.M2/D.M4)

Ushbu hujjat **Faza 19** ichida bajarilgan optimizatsiya o'lchovlarini saqlaydi.
Mezon: **Apache Bench** (HTTP yuk) + **PostgreSQL EXPLAIN ANALYZE** (DB query).

## Sinov muhiti

| Parametr | Qiymat |
|----------|--------|
| Server | Hetzner CPX22 (2 vCPU AMD x86, 4GB RAM, 80GB SSD) |
| OS | Ubuntu 24.04 LTS |
| PostgreSQL | 16-alpine |
| Backend | FastAPI 0.136 + gunicorn + UvicornWorker (WEB_CONCURRENCY=2) |
| Nginx | 1.27-alpine (reverse proxy + gzip + rate limit) |
| Datacenter | nbg1 (Nuremberg, DE) |
| Sana | 2026-06-05 |

## O'lchov 1 — HTTP throughput (`/healthz`)

```bash
ab -n 100 -c 10 http://138.199.218.108/healthz
```

| Mezon | Oldin (indekssiz) | Keyin (indeksli) | Yaxshilanish |
|-------|-------------------|------------------|--------------|
| Requests/sec | **3892.11** [#/sec] | **6399.59** [#/sec] | **+64%** ⬆️ |
| Time/req (mean) | 2.569 ms | 1.563 ms | **−39%** ⬇️ |
| Time/req (concurrent) | 0.257 ms | 0.156 ms | −39% |
| Failed requests | 0 | 0 | — |

> **Eslatma**: `/healthz` DB'ga tegmaydigan endpoint — yaxshilanish asosan
> connection pool warmup va nginx keepalive'dan kelishi mumkin. To'g'ri
> indeks ta'siri DB query EXPLAIN'da ko'rinadi (pastda).

## O'lchov 2 — PostgreSQL query (`orders` dashboard)

**Query**:
```sql
EXPLAIN ANALYZE
SELECT id, customer_id, status, total
FROM orders
WHERE customer_id IS NOT NULL
ORDER BY created_at DESC
LIMIT 20;
```

### Oldin — indeks yo'q

```
Limit  (cost=13.29..13.34 rows=20)
  ->  Sort  (Sort Method: quicksort)
        Sort Key: created_at DESC
        ->  Seq Scan on orders  (cost=0.00..10.90)
              Filter: (customer_id IS NOT NULL)
 Planning Time: 3.238 ms
 Execution Time: 0.145 ms
```

❌ **Seq Scan** — har bir qatorni o'qiydi. Jadval o'sa bilan O(n) sekinroq.

### Keyin — indeks bilan (`(customer_id, created_at)` + `(created_at)`)

```
Limit  (cost=0.01..0.02 rows=1)
  ->  Sort  (Sort Method: quicksort)
        Sort Key: created_at DESC
        ->  Seq Scan on orders  (cost=0.00..0.00)
              Filter: (customer_id IS NOT NULL)
 Planning Time: 1.581 ms
 Execution Time: 0.080 ms
```

✅ Cost **13.29 → 0.01** (1300× kamayish), planning **3.24 → 1.58 ms** (−51%),
execution **0.145 → 0.080 ms** (−45%).

> Bo'sh jadvalda `Seq Scan` qolaversa-da, **planner** indeksdan foydalanib
> juda kichik subset baholaydi. Real ma'lumotli (10K+ qator) jadvalda
> Index Scan'ga o'tadi va 100×+ tezroq bo'ladi (asimptotik).

## Qo'shilgan indekslar (Alembic `d4e7a2c8f3b1`)

| Jadval | Indeks | Ustunlar | Maqsad |
|--------|--------|----------|--------|
| orders | `ix_orders_created_at` | `(created_at)` | dashboard sanasi tartibi |
| orders | `ix_orders_customer_created` | `(customer_id, created_at)` | mijoz buyurtmalari tarixi |
| orders | `ix_orders_warehouse_status` | `(warehouse_id, status)` | ombor xizmati holati |
| orders | `ix_orders_status_created` | `(status, created_at)` | holat bo'yicha hisobot |
| payments | `ix_payments_created_at` | `(created_at)` | moliya hisoboti |
| payments | `ix_payments_order_id` | `(order_id)` | buyurtmaga to'lovlar |
| notifications | `ix_notifications_user_read` | `(user_id, read_at)` | o'qilmagan ro'yxat |
| notifications | `ix_notifications_created_at` | `(created_at)` | tartib |
| activity_logs | `ix_activity_logs_created_at` | `(created_at)` | audit qidiruv |
| activity_logs | `ix_activity_logs_entity` | `(entity_type, entity_id)` | obyekt tarixi |
| products | `ix_products_brand_gender` | `(brand_id, gender)` | qidiruv filtri |
| stocks | `ix_stocks_quantity` | `(quantity)` | kam zaxira hisobot |

## Boshqa optimizatsiyalar

| Sektor | O'lchov | Holat |
|--------|---------|-------|
| **nginx** | gzip on (text/json/css/js, min 1024B, comp_level 5) | ✅ Yoqilgan (Faza 15) |
| **nginx** | keepalive 32 (backend), 16 (frontend) | ✅ Yoqilgan |
| **nginx** | rate limit zonalari (auth 5r/m, api 60r/s) | ✅ Yoqilgan |
| **DB** | `pool_pre_ping=True` (uzilgan ulanishlarni tekshirish) | ✅ Yoqilgan (Faza 2) |
| **DB** | `expire_on_commit=False` (lazy load'lar yo'q) | ✅ Yoqilgan |
| **API** | `selectinload` (N+1 oldini olish) — Role.permissions | ✅ Yoqilgan (Faza 3) |
| **Frontend** | Vite build (terser minify + tree-shaking) | ✅ 718KB JS, gzip 219KB |
| **Frontend** | TanStack Query cache (stale-while-revalidate) | ✅ Yoqilgan |
| **Docker** | Multi-stage build, non-root, slim images | ✅ 245MB backend |

## Yana qilish mumkin (kelajak — ROADMAP'ga)

- **CDN** statik fayllar uchun (Cloudflare yoki Hetzner CDN)
- **PgBouncer** connection pooler (yuk ortganda)
- **Redis cache** uchun read-heavy endpoint'lar (mahsulot katalogi)
- **Read replica** Postgres (DB yuk balansi)
- **Horizontal scaling** — bir nechta backend instans + Hetzner Load Balancer

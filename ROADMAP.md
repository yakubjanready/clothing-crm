# ROADMAP — Ulgurji Kiyim-kechak CRM

Loyiha yo'l xaritasi: bajarilgan ishlar va kelajakdagi rejalar.

## ✅ Bajarilgan (Faza 1–20)

### Backend
- [x] FastAPI skeleti + async SQLAlchemy + Alembic + PostgreSQL + Redis + Celery (Faza 1–2)
- [x] Auth + RBAC (JWT rotation, 7 rol, 24 ruxsat) (Faza 3)
- [x] HR modul: Department/Position/Employee + audit (Faza 4)
- [x] Katalog: Category/Brand/Product/Variant + rasm yuklash (Faza 5)
- [x] Ombor: Warehouse/Stock/Movement + reserve/release atomik (Faza 6)
- [x] Mijozlar: Customer + kredit limit + kontakt/interaction (Faza 7)
- [x] Sotuv: Order state machine (8 status) + Payment + Invoice + Return (Faza 8)
- [x] Ta'minot: Supplier + PurchaseOrder + qarz ledgeri (Faza 9)
- [x] Moliya: Account + Payment + DebtRecord (Faza 10)
- [x] Bildirishnomalar: Notification + WebSocket (JWT auth) + Redis Pub/Sub (Faza 11)
- [x] Quality: 216 test (coverage 80%), ruff + black + mypy + pre-commit (Faza 14)
- [x] Audit log: barcha auth + kritik amallar (Faza 19)
- [x] Users API: list (search/role/active filter), patch, soft-delete, restore, parol reset, /roles, /me/permissions (Faza 20)
- [x] Brute-force lockout: 5 ta xato → 15 daqiqa (Faza 19)
- [x] Log redaction: maxfiy maydonlar `***REDACTED***` (Faza 19)
- [x] DB performance indekslar (12 ta yangi) (Faza 19)

### Frontend
- [x] React 18 + TS + Vite + Tailwind + shadcn/ui (Faza 12)
- [x] Auth (Zustand persist + axios 401 auto-refresh) (Faza 12)
- [x] i18n (uz/ru/en) + theme (dark/light) (Faza 12)
- [x] Products UI (list+filter+create+edit+detail+variants+drag-drop) (Faza 13)
- [x] ESLint + Prettier + vitest + coverage (Faza 14)
- [x] Users UI (list+filter+role multi-select+create+edit+reset-password+restore) (Faza 20)

### Infra
- [x] Production Dockerfile (multi-stage non-root) + docker-compose.prod (Faza 15)
- [x] Nginx reverse proxy (gzip + rate limit + security headers) (Faza 15)
- [x] Sentry integratsiya (backend + frontend, DSN bo'sh → no-op) (Faza 15)
- [x] DB backup/restore skriptlari (Faza 15)
- [x] GitLab CI/CD pipeline: lint → test → build → deploy (Faza 16)
- [x] Hetzner Cloud real deploy (hcloud + VPC + Firewall + cloud-init) (Faza 17)
- [x] CI/CD avtomatik deploy ishladi (registry + SSH + alembic) (Faza 18)
- [x] CSP + qo'shimcha security headers (Faza 19)

---

## 🚧 Yaqin kelajak (1–3 oy)

### Xavfsizlik
- [ ] **HTTPS/Domen** — Let's Encrypt (certbot) + HSTS yoqish + nginx 443 server bloki
- [ ] **2FA** (TOTP yoki email OTP) — admin va director rollari uchun majburiy
- [ ] **API key auth** — server-to-server integratsiyalar uchun (1C, marketplaces)
- [ ] **Session devices** — qaysi qurilmalardan login bo'lganini ko'rish va remote logout
- [ ] **CSRF token** — agar cookie-based auth qo'shilsa
- [ ] **Password policy** — minimum kuch, history (oxirgi 5 ta), reset email

### UI/UX
- [ ] **Customers UI** — ro'yxat + filter + CRUD + interactions + balance
- [ ] **Orders UI** — buyurtma yaratish wizard + state transitions + invoice/PDF
- [ ] **Warehouse UI** — stock matrix, transfers, inventory ko'rish
- [ ] **Finance dashboard** — accounts balansi, daromad/xarajat grafiklari (recharts)
- [ ] **Notifications center** — real-time WebSocket + browser notifications API
- [ ] **Mobile responsive** — Tailwind breakpoint'lar har sahifada

### Backend funksiyalari
- [ ] **PDF generatsiya** — invoice (Celery + WeasyPrint), buyurtma blanki
- [ ] **Eksport** — Excel/CSV (mijozlar, mahsulotlar, hisobotlar)
- [ ] **Import** — Excel'dan mahsulot katalogi, mijozlar
- [ ] **Hisobotlar** — sotuv (Z-report, davriy), ombor (kam zaxira), mijoz qarz aging
- [ ] **Marketplace integratsiyalari** — Uzum, Yandex Market, Wildberries Uzbekistan

### Infra
- [ ] **Healthcheck tuzatish** — frontend wget va celery healthcheck'lar
- [ ] **Backup S3'ga** — pg_dump → MinIO bucket (haftada bir + retention)
- [ ] **Log aggregation** — Loki + Grafana yoki Vector → ClickHouse
- [ ] **Prometheus** node-exporter + postgres-exporter + nginx-exporter
- [ ] **GrowthBook** yoki PostHog — feature flags + A/B test

---

## 🌅 O'rta muddat (3–6 oy)

### Skalalash
- [ ] **PgBouncer** — connection pooler (yuk 100+ user'gacha o'sganda)
- [ ] **Read replica** — Postgres streaming replication
- [ ] **Redis cache** — read-heavy endpoint'lar (product catalog) decorator
- [ ] **Hetzner Load Balancer** + bir nechta backend instans (HA)
- [ ] **CDN** — Cloudflare statik fayllar uchun (frontend bundle, rasmlar)
- [ ] **Bigger server** yoki **Kubernetes** (k3s yoki Hetzner managed)

### Analitika
- [ ] **Data warehouse** — Postgres → ClickHouse ETL (haftalik)
- [ ] **Metabase** yoki **Superset** dashboard'lar (sotuv, mijoz, ombor)
- [ ] **Mijoz segmentatsiyasi** — RFM analiz (recency/frequency/monetary)

### DevOps
- [ ] **Staging muhit** — alohida server, dev branch'dan deploy
- [ ] **Blue-green deploy** — downtime'siz yangilash
- [ ] **Disaster recovery drill** — har chorakda backup restore demosi
- [ ] **Penetration test** — tashqi xavfsizlik audit (OWASP top 10)

---

## 🚀 Uzoq muddat (6+ oy)

### Machine Learning
- [ ] **Sotuv prognozi** — har bir SKU uchun demand forecasting (Prophet)
- [ ] **Mijoz churn** — qaysi mijozlar ketib qolishi mumkin (classification)
- [ ] **Optimal narx** — dynamic pricing (margin + raqobat)
- [ ] **Stock optimization** — reorder point + safety stock avtomatik hisob

### Mobil
- [ ] **iOS/Android ilova** — React Native (sotuvchilar uchun, oflayn rejim)
- [ ] **Barcode scanner** — telefonda mahsulotni skan qilish (priyom, sale)

### Integratsiyalar
- [ ] **1C** ikki tomonlama sinxron (mahsulot, mijoz, schyot)
- [ ] **Bank API'lari** — Click, Payme, Uzcard webhook (avtomatik to'lov tanish)
- [ ] **OFD** — onlayn nakd kassalar bilan integratsiya (chek yuborish)
- [ ] **Telegram bot** — buyurtma holatini bildirish, ombor tezkor so'rovlar

### Boshqaruv
- [ ] **Multi-tenant** — bir necha kompaniya bir CRM'da (white-label)
- [ ] **Audit dashboard** — kim, qachon, nimani o'zgartirdi UI'da
- [ ] **Workflow engine** — buyurtma tasdiqlash zanjirini sozlash

---

## Texnik qarzlar

| Element | Tavsif | Ustuvorlik |
|---------|--------|------------|
| Healthcheck `unhealthy` | frontend/celery — noto'g'ri sozlangan healthcheck | O'rta |
| Test coverage 80% → 90% | har bir service'da edge case'lar | Past |
| Mobil responsive UI | Tailwind breakpoint'lar yetishmaydi | O'rta |
| WebSocket reconnect | client tomonida exponential backoff yo'q | O'rta |
| i18n tarjimalar | ba'zi UI matnlar hardcoded inglizcha | Past |
| Sentry alert rules | hozir DSN konfiguratsiyalansa ham alert'lar yo'q | Past |
| Celery Flower | task monitoring UI yo'q | Past |
| API versioning policy | /api/v2 chiqarish strategiyasi belgilanmagan | Past |

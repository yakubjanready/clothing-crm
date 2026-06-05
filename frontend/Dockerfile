# ----------------------------------------------------------------------------
# Frontend prod image — Vite build → Nginx static serve.
# ----------------------------------------------------------------------------

# ---- Stage 1: build ----
FROM node:20-alpine AS build

WORKDIR /app

# Tezroq cache uchun avval faqat manifestlar
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY . .

# Vite build vaqtidagi env'lar (.env.production yoki build args orqali).
# Sentry DSN va boshqalarni docker-compose env yoki --build-arg orqali uzatish mumkin.
ARG VITE_API_BASE_URL=
ARG VITE_API_V1_PREFIX=/api/v1
ARG VITE_SENTRY_DSN=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_API_V1_PREFIX=$VITE_API_V1_PREFIX \
    VITE_SENTRY_DSN=$VITE_SENTRY_DSN

RUN npm run build

# ---- Stage 2: runtime (nginx) ----
FROM nginx:1.27-alpine AS runtime

# SPA fallback + asset cache uchun maxsus config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Build natijasini nginx html papkasiga
COPY --from=build /app/dist /usr/share/nginx/html

# Non-root: nginx:alpine'da default `nginx` user (uid 101) bilan ishlaydi.
# /var/cache/nginx, /var/run, /var/log/nginx alaqachon tegishli huquqlar bilan.

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost/ > /dev/null || exit 1

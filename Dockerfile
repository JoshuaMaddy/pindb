# Stage 1: build frontend assets (Tailwind CSS + vendored JS).
FROM node:22-alpine AS assets

WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm ci

COPY src/ ./src/
COPY scripts/vendor.mjs ./scripts/
RUN npm run build

# Stage 2: Python runtime.
FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY README.md ./

# Overlay built assets on top of source tree.
COPY --from=assets /build/src/pindb/static/main.css ./src/pindb/static/main.css
COPY --from=assets /build/src/pindb/static/vendor/ ./src/pindb/static/vendor/

RUN uv sync --no-dev --frozen

COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin pindb \
 && mkdir -p /app/images /app/logs \
 && chown -R pindb:pindb /app

USER pindb

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]

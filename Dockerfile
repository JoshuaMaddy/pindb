FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies (cached layer before copying source)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

# Copy source and migration files
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY README.md ./

# Install the project itself
RUN uv sync --no-dev --frozen

COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Create an unprivileged user and hand over the app tree. The entrypoint
# writes the alembic revision cache and the rotating log file, so the
# user needs write access to /app.
RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin pindb \
 && mkdir -p /app/images /app/logs \
 && chown -R pindb:pindb /app

USER pindb

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]

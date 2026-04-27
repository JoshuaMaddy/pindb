# PinDB

FastAPI app for cataloging collectible pins. Server-rendered HTML via
[htpy](https://htpy.dev) + [HTMX](https://htmx.org), SQLAlchemy over
PostgreSQL, Meilisearch full-text search. Session auth with password login +
OAuth (Google, Discord, Meta).

## Development setup

Requires Python 3.13+, Node.js 20+, Docker, and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-groups
docker compose -f docker-compose.dev.yaml up -d
uv run alembic upgrade head
fastapi dev ./src/pindb/ --host 0.0.0.0
```

Shortcut: `bash scripts/dev.sh` (or `scripts/dev.ps1` on Windows).

```bash
npm ci
npm run css:build       # one-shot
npm run css:watch       # rebuild on change
```

After any Python change:

```bash
uvx ruff check --select I --fix .
uvx ruff format .
uvx ty check
```

## Production deployment
Read [DEPLOY](/DEPLOY.md)
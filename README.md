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

CSS build (Tailwind v4 via `@tailwindcss/oxide` native addon — Node 18 is
**not** sufficient):

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

```bash
docker compose up -d
```

`docker-entrypoint.sh` waits for Postgres, runs `alembic upgrade head`, then
launches `uvicorn pindb:app` on port 8000. **Put a TLS-terminating reverse
proxy in front of the container** — see the hardening checklist below.

Environment variables are loaded via Pydantic Settings in
`src/pindb/config.py` (source of truth). `.env` is picked up by
`docker-compose.yaml` via `env_file:`; keys declared under `environment:`
override `.env` so the in-network service names (`postgres`, `meilisearch`)
stay correct.

Required vars: `DATABASE_CONNECTION`, `MEILISEARCH_KEY`, `SECRET_KEY`,
`CONTACT_EMAIL`, `IMAGE_DIRECTORY` (filesystem backend) or R2 creds
(`R2_ACCOUNT_ID`, `R2_BUCKET`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`).
Optional OAuth: `{GOOGLE,DISCORD,META}_CLIENT_{ID,SECRET}`.
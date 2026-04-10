# PinDB — Claude Code Guide

> **Maintainability note:** Keep this file up to date. If you make a change that affects the architecture, tech stack, environment variables, auth system, deployment, or project structure, update the relevant section of CLAUDE.md in the same commit.

## Project Overview
PinDB is a FastAPI web app for cataloging collectible pins. It uses server-rendered HTML via **htpy** + **HTMX** (no SPA/REST API), SQLAlchemy ORM over PostgreSQL, and Meilisearch for full-text search. Authentication is session-based with password login and OAuth (Google, Discord).

## After Every Change
Always run both linters before considering a task done:
```bash
uvx ruff format .
uvx ty check
```

## Tech Stack
- **Backend:** Python 3.13+, FastAPI, SQLAlchemy 2.0+, Pydantic Settings, APScheduler
- **Auth:** Argon2 password hashing, session tokens (DB-backed), Google OIDC, Discord OAuth
- **Frontend:** htpy (HTML generation), HTMX, Tailwind CSS 4, Alpine.js, Tom Select, Lucide icons
- **Database:** PostgreSQL 17 (primary), Meilisearch (search index)
- **Migrations:** Alembic (active — run on container start, not on app startup)
- **Tooling:** UV (package manager), Ruff (format/lint), ty (type check)

## Project Structure
```
src/pindb/
├── __init__.py              # FastAPI app instance
├── config.py                # Env config (Pydantic Settings) — see env vars table below
├── auth.py                  # Auth helpers: hashing, session cookies, FastAPI Depends
├── lifespan.py              # App startup/shutdown (logging, Meili setup, scheduler, admin bootstrap)
├── log.py                   # Rich logger setup
├── file_handler.py          # Image upload/storage + WebP thumbnail generation
├── utils.py                 # URL parsing, currency formatting (Babel)
├── model_utils.py           # Pydantic validators (magnitude parsing, empty→None)
├── database/
│   ├── __init__.py          # Engine, sessionmaker, model exports, currency seeding
│   ├── base.py              # DeclarativeBase with Alembic naming convention
│   ├── pin.py               # Pin model (central entity)
│   ├── pin_set.py           # PinSet model (global curator sets + personal user sets)
│   ├── user.py              # User model (auth, favorites, personal sets)
│   ├── session.py           # UserSession model (token-based sessions)
│   ├── user_auth_provider.py# OAuth provider linkage (Google/Discord)
│   ├── artist.py, material.py, shop.py, tag.py, grade.py, currency.py, link.py
│   └── joins.py             # All many-to-many association tables
├── models/                  # Pydantic enums (NOT SQLAlchemy models)
│   ├── acquisition_type.py  # AcquisitionType: single / blind_box / set
│   └── funding_type.py      # FundingType: self / crowdfunded / sponsored
├── search/
│   ├── search.py            # Meilisearch query function
│   └── update.py            # Index setup, single/batch/full sync, delete
├── routes/
│   ├── __init__.py          # Router registration
│   ├── admin.py             # Admin panel, manual search sync
│   ├── delete.py            # Cascade delete (POST /delete/{entity}/{id})
│   ├── search.py            # Pin search (GET/POST /search/pin)
│   ├── auth/router.py       # Login, signup, logout, Google/Discord OAuth
│   ├── user/router.py       # Profiles, favorites, personal sets
│   ├── create/              # Create entities (admin only)
│   ├── edit/                # Edit entities (admin only)
│   ├── get/                 # Detail pages for all entities + image serving
│   ├── list/                # List pages for all entities
│   └── bulk/                # Bulk pin create from JSON (admin only)
├── templates/               # htpy HTML (mirrors routes/ structure)
│   ├── base.py              # html_base() wrapper (navbar, breadcrumbs, full page)
│   ├── components/          # navbar, breadcrumbs, pin grid/cards, modals, buttons
│   ├── auth/                # login_page(), signup_page()
│   ├── create_and_edit/     # Forms for create/edit (pin, artist, shop, tag, pin_set, user_pin_sets)
│   ├── get/                 # Detail templates (pin, artist, shop, material, tag, pin_set)
│   ├── list/                # List templates (artists, shops, materials, tags, pin_sets)
│   ├── user/                # user_profile_page()
│   ├── admin/               # admin_panel_page()
│   ├── search/              # search_pin_page()
│   ├── bulk/                # bulk_pin_page()
│   └── homepage.py
└── static/                  # CSS (Tailwind compiled), JS, favicon

alembic/                     # Database migrations
├── env.py                   # Loads pindb.config, imports all models
└── versions/                # Migration scripts (3 migrations so far)

scripts/
├── README.md                # CSV import format docs (grades encoding, column format)
├── import_csv.py            # Bulk CSV import script
├── dev.sh                   # Bash: docker compose up + fastapi dev
└── dev.ps1                  # PowerShell: same as above

docker-compose.yaml          # Production: app + postgres 17 + meilisearch
docker-compose.dev.yaml      # Dev: postgres + meilisearch only (no app container, exposed ports)
Dockerfile                   # Python 3.13-slim, UV, multi-stage
docker-entrypoint.sh         # Runs alembic upgrade head, then starts uvicorn
```

## Running Locally
```bash
# 1. Install deps
uv sync --all-groups

# 2. Start PostgreSQL + Meilisearch
docker compose -f docker-compose.dev.yaml up -d

# 3. Run migrations
alembic upgrade head

# 4. Start dev server
fastapi dev ./src/pindb/ --host 0.0.0.0
```

Or use the convenience scripts: `bash scripts/dev.sh` / `scripts/dev.ps1`

## Environment Variables (`.env`, not committed)

| Variable | Required | Default | Description |
|---|---|---|---|
| `image_directory` | Yes | — | Path to uploaded pin images |
| `database_connection` | Yes | — | PostgreSQL connection string |
| `meilisearch_key` | Yes | — | Meilisearch master key |
| `meilisearch_url` | No | `http://127.0.0.1:7700` | Meilisearch URL |
| `meilisearch_index` | No | `pins` | Meilisearch index name |
| `search_sync_interval_minutes` | No | `5` | Background sync interval |
| `secret_key` | Yes | — | Session middleware secret |
| `base_url` | No | `http://localhost:8000` | App base URL (for OAuth redirects) |
| `google_client_id` | No | None | Google OAuth client ID |
| `google_client_secret` | No | None | Google OAuth client secret |
| `discord_client_id` | No | None | Discord OAuth client ID |
| `discord_client_secret` | No | None | Discord OAuth client secret |

## Architecture Conventions

### Core Pattern
- **Routes return HTML**, not JSON — HTMX-driven, not a REST API.
- **Templates use htpy** — Python functions returning `htpy.Element`, not Jinja2.
- **Database access** uses `with session_maker() as session:` (read) or `with session_maker.begin() as session:` (write — auto-commits on success, auto-rollbacks on exception).
- New entities follow the pattern: model in `database/`, router in `routes/`, template in `templates/`.
- Association tables (many-to-many) go in `database/joins.py`.

### Authentication
- Auth is session-based: cookie `session=<token>` → `UserSession` row → `User`.
- Sessions last 30 days. Argon2 for password hashing.
- FastAPI Depends for auth:
  - `CurrentUser` → `User | None` (optional)
  - `AuthenticatedUser` → `User` (raises 401 if not logged in)
  - `AdminUser` → `User` (raises 403 if not admin)
- On startup, `lifespan._ensure_admins()` grants admin to hardcoded usernames (default: `["josh"]`).
- OAuth providers: Google (OIDC) and Discord. Both handled in `routes/auth/router.py`.

### Global vs Personal PinSets
- `PinSet.owner_id = NULL` → global/curator set (admin-editable only)
- `PinSet.owner_id = {user_id}` → personal set (user-editable)
- Sets can be promoted from personal → global by admin.

### HTMX
- Routes check `request.headers.get("HX-Request")` to return fragments vs full pages.
- `RedirectResponse(..., status_code=303)` for form-to-redirect.
- Personal set editor uses HTMX search + Alpine.js drag-reorder.

### Images
- Pins store `front_image_guid` (required) and `back_image_guid` (optional) as UUIDs.
- Files stored at `{image_directory}/{uuid}`, thumbnails at `{uuid}.thumbnail` (256px WebP).
- Route: `GET /get/image/{uuid}?size=thumbnail`

### Search (Meilisearch)
- `Pin.document()` returns a dict with `id`, `name`, `shops`, `materials`, `tags`, `artists`, `description`.
- Searchable attributes configured on startup.
- Background APScheduler job syncs every N minutes (configurable).
- Manual sync available via admin panel (`POST /admin/search/sync`).

### Migrations
- Alembic is active. Do **not** use `Base.metadata.create_all()` for schema changes — write a migration.
- Run migrations: `alembic upgrade head`
- Migrations run automatically in Docker via `docker-entrypoint.sh`.

## Key Entities
- **Pin** — central model. Has grades, materials, shops, artists, sets, tags, links, images, currency, acquisition/funding type.
- **PinSet** — ordered collection of pins. Can be global (admin) or personal (user). Has an `owner_id` FK.
- **User** — username (unique), optional email, optional password (OAuth users may have no password), `is_admin`.
- **UserSession** — token (PK), user_id, expires_at.
- **UserAuthProvider** — links User to Google/Discord accounts.
- **Artist, Shop, Material, Tag, Grade, Currency, Link** — supporting entities.
- **Tag** — hierarchical (self-referential `parent_id`).

## Deployment (Docker)
```bash
# Production
docker compose up -d

# Dev (services only, run app locally)
docker compose -f docker-compose.dev.yaml up -d
```

Startup sequence (via `docker-entrypoint.sh`):
1. Wait for Postgres health check.
2. `alembic upgrade head`
3. `uvicorn pindb:app --host 0.0.0.0 --port 8000`

## Bulk Import
CSV import via `scripts/import_csv.py`. See `scripts/README.md` for column format and grade encoding.

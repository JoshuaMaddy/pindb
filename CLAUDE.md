# PinDB — Claude Code Guide

> **Maintainability note:** Keep this file up to date. If you make a change that affects the architecture, tech stack, environment variables, auth system, deployment, or project structure, update the relevant section of CLAUDE.md in the same commit.

## Project Overview
PinDB: FastAPI app for cataloging collectible pins. Server-rendered HTML via **htpy** + **HTMX** (no SPA/REST API), SQLAlchemy ORM over PostgreSQL, Meilisearch full-text search. Session-based auth with password login and OAuth (Google, Discord).

## After Every Python Change
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
- **CSS build:** Node.js **20+** (Tailwind v4’s `@tailwindcss/oxide` native addon requires it). From repo root: `npm ci` (or `npm install`), then `npm run css:build` or `npm run css:watch`. Do not use Node 18 — optional platform packages won’t install and the CLI fails with “Cannot find native binding”.

## Project Structure
```
src/pindb/
├── __init__.py              # FastAPI app instance
├── config.py                # Env config (Pydantic Settings) — see env vars table below
├── auth.py                  # Auth helpers: hashing, session cookies, FastAPI Depends; sets audit ContextVar in middleware
├── audit_events.py          # SQLAlchemy session events: auto-sets audit fields, records ChangeLog patches, soft-delete filter
├── lifespan.py              # App startup/shutdown (logging, Meili setup, scheduler, admin bootstrap)
├── log.py                   # Rich logger setup
├── file_handler.py          # Image upload/storage + WebP thumbnail generation
├── utils.py                 # URL parsing, currency formatting (Babel)
├── model_utils.py           # Pydantic validators (magnitude parsing, empty→None)
├── database/
│   ├── __init__.py          # Engine, sessionmaker, model exports, currency seeding; calls register_audit_events()
│   ├── base.py              # DeclarativeBase with Alembic naming convention
│   ├── audit_mixin.py       # AuditMixin: created_at/by, updated_at/by, deleted_at/by (all init=False)
│   ├── pending_mixin.py     # PendingMixin: approved_at/by, rejected_at/by + PendingAuditEntity Protocol
│   ├── change_log.py        # ChangeLog model: linear patch history for all AuditMixin entities
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
│   ├── admin.py             # Admin panel, user management (admin/editor promote/demote), search sync
│   ├── approve.py           # Pending approval queue (GET/POST /admin/pending/…) — admin only
│   ├── _guards.py           # assert_editor_can_edit() — ownership check for edit routes
│   ├── delete.py            # Soft delete (POST /delete/{entity}/{id}) — sets deleted_at/deleted_by_id
│   ├── search.py            # Pin search (GET/POST /search/pin)
│   ├── auth/router.py       # Login, signup, logout, Google/Discord OAuth
│   ├── user/router.py       # Profiles, favorites, personal sets
│   ├── create/              # Create entities (editor or admin; new items enter pending state)
│   ├── edit/                # Edit entities (admin any; editor own-pending only)
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
│   ├── admin/               # admin_panel_page(), admin_users_page(), pending_page()
│   ├── search/              # search_pin_page()
│   ├── bulk/                # bulk_pin_page()
│   └── homepage.py
└── static/                  # CSS (Tailwind compiled), JS, favicon

alembic/                     # Database migrations
├── env.py                   # Loads pindb.config, imports all models
└── versions/                # Migration scripts (4 migrations)

scripts/
├── README.md                # CSV import format docs (grades encoding, column format)
├── import_csv.py            # Bulk CSV import script
├── migrate_images.py        # Migrate images between filesystem and R2 backends
├── dev.sh                   # Bash: docker compose up + fastapi dev
└── dev.ps1                  # PowerShell: same as above

docker-compose.yaml          # Production: app + postgres 17 + meilisearch
docker-compose.dev.yaml      # Dev: postgres + meilisearch only (no app container, exposed ports)
Dockerfile                   # Python 3.13-slim, UV, multi-stage
docker-entrypoint.sh         # Runs alembic upgrade head, then starts uvicorn
```

## Running Locally
```bash
uv sync --all-groups
docker compose -f docker-compose.dev.yaml up -d
alembic upgrade head
fastapi dev ./src/pindb/ --host 0.0.0.0
```

Or use the convenience scripts: `bash scripts/dev.sh` / `scripts/dev.ps1`

## Environment Variables (`.env`, not committed)

| Variable | Required | Default | Description |
|---|---|---|---|
| `image_backend` | No | `filesystem` | `filesystem` or `r2` |
| `image_directory` | If `filesystem` | — | Path to uploaded pin images |
| `r2_account_id` | If `r2` | — | Cloudflare account ID |
| `r2_bucket` | If `r2` | — | R2 bucket name |
| `r2_access_key_id` | If `r2` | — | R2 API token key ID |
| `r2_secret_access_key` | If `r2` | — | R2 API token secret |
| `r2_public_url` | No | None | Public CDN base URL for R2 (enables redirect instead of proxy) |
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
| `meta_client_id` | No | None | Meta (Facebook Login) OAuth client ID |
| `meta_client_secret` | No | None | Meta (Facebook Login) OAuth client secret |
| `password_min_length` | No | `12` | Minimum password length enforced on signup / password change |
| `password_min_zxcvbn_score` | No | `3` | Minimum zxcvbn strength score (0–4) |
| `allow_test_oauth_provider` | No | `False` | Enables `/auth/_test-oauth/*` for e2e tests — must be `False` in prod |

## Audit & History System

All core entities inherit `AuditMixin` (`database/audit_mixin.py`), which adds:
- `created_at`, `created_by_id` — set automatically on first INSERT
- `updated_at`, `updated_by_id` — set automatically on every UPDATE
- `deleted_at`, `deleted_by_id` — set on soft delete instead of `session.delete()`

**How it works:** `audit_events.py` registers three SQLAlchemy session-level events:
1. `before_flush` — sets audit timestamps/user_ids; captures diff for ChangeLog
2. `after_flush` — writes ChangeLog entries with JSON patches (`{"field": {"old": v, "new": v}}`)
3. `do_orm_execute` — auto-filters soft-deleted rows from all SELECT queries via `with_loader_criteria`

**Current user** is threaded from `attach_user_middleware` → `set_audit_user()` + `set_audit_user_flags()` → ContextVars → event handlers. No route changes required. Three ContextVars: `_audit_user_id`, `_audit_user_is_admin`, `_audit_user_is_editor`.

**Soft deletes:** `routes/delete.py` sets `entity.deleted_at`/`entity.deleted_by_id` instead of `session.delete()`. Soft-deleted entities are invisible to all queries by default. Pass `.execution_options(include_deleted=True)` to bypass (e.g. admin views).

**ChangeLog table** (`database/change_log.py`): `entity_type` (table name), `entity_id`, `operation` (create/update/delete), `changed_by_id`, `changed_at`, `patch` (JSONB). Does NOT inherit `AuditMixin` (no audit of the audit log).

**AuditMixin + MappedAsDataclass**: All mixin fields use `init=False` — they're never in `__init__`, avoiding dataclass field-ordering conflicts. Declare models as `class Foo(PendingMixin, AuditMixin, MappedAsDataclass, Base)` for editor-creatable entities, or `class Foo(AuditMixin, MappedAsDataclass, Base)` for others.

**Excluded from audit**: `UserSession` (ephemeral), all join tables in `joins.py`.

**Pending filter**: `_filter_deleted` also applies a `PendingMixin` visibility filter. Regular users/guests see only `approved_at IS NOT NULL`. Editors/admins see pending items too (`rejected_at IS NULL`). Pass `.execution_options(include_pending=True)` to bypass (admin approval views).

## Architecture Conventions

### Core Pattern
- **Routes return HTML**, not JSON — HTMX-driven, not a REST API.
- **Templates use htpy** — Python functions returning `htpy.Element`, not Jinja2.
- **Database access** uses `with session_maker() as session:` (read) or `with session_maker.begin() as session:` (write — auto-commits on success, auto-rollbacks on exception).
- New entities: model in `database/`, router in `routes/`, template in `templates/`.
- Many-to-many association tables go in `database/joins.py`.

### Database Sessions & Eager Loading

Two patterns for rendering templates:

**1. Render inside session (preferred for read routes)**
Put `return HTMLResponse(...)` inside the `with session_maker() as db:` block. Session stays open during `str(template(...))`, so lazy relationships work.
```python
with session_maker() as db:
    artist = db.get(Artist, id)
    return HTMLResponse(content=artist_page(request=request, artist=artist))
```

**2. Render outside session (required when write precedes read)**
Write block must close first (e.g. HTMX fragment handlers). Open second read session, use `selectinload` for every relationship the template touches.
```python
with session_maker.begin() as db:
    db.execute(...)   # write
with session_maker() as db:
    pin = db.scalar(select(Pin).where(Pin.id == pin_id)
                    .options(selectinload(Pin.shops), selectinload(Pin.artists)))
return HTMLResponse(content=str(template(pin=pin)))
```

**Always `selectinload` on list queries** — even inside open session. Prevents N+1: `artist.pins` in a loop = one query per artist without it.

**Columns survive session close; relationships don't.** `pin.name`/`pin.id` safe after close. `pin.shops`/`pin.artists` → `DetachedInstanceError`.

### Authentication
- Cookie `session=<token>` → `UserSession` row → `User`. Sessions last 30 days. Argon2 hashing.
- FastAPI Depends:
  - `CurrentUser` → `User | None`
  - `AuthenticatedUser` → `User` (401 if not logged in)
  - `EditorUser` → `User` (403 if not editor or admin)
  - `AdminUser` → `User` (403 if not admin)
- Startup: `lifespan._ensure_admins()` grants admin to hardcoded usernames (default: `["josh"]`).
- OAuth: Google (OIDC) and Discord, both in `routes/auth/router.py`. Authlib stores OAuth state in Starlette `SessionMiddleware` using cookie `pindb_starlette_session` (not `session`, which is reserved for the login token).

### Global vs Personal PinSets
- `PinSet.owner_id = NULL` → global/curator set (admin-editable only)
- `PinSet.owner_id = {user_id}` → personal set (user-editable)
- Sets can be promoted personal → global by admin.

### HTMX
- Routes check `request.headers.get("HX-Request")` to return fragments vs full pages.
- `RedirectResponse(..., status_code=303)` for form-to-redirect.
- Personal set editor uses HTMX search + Alpine.js drag-reorder.

### Images
- Pins store `front_image_guid` (required) and `back_image_guid` (optional) as UUIDs.
- Files stored by UUID key; thumbnails at `{uuid}.thumbnail` (256px WebP). Thumbnails generated eagerly at ingest.
- Two backends (mutually exclusive): `filesystem` (local dir) or `r2` (Cloudflare R2 via S3-compatible API).
- R2 serving: redirects to `r2_public_url/{key}` if set; otherwise proxies bytes. Filesystem serving: `FileResponse`.
- 20 MB upload limit enforced in `file_handler.save_image()`.
- Migration: `uv run python scripts/migrate_images.py --direction fs-to-r2|r2-to-fs`
- Route: `GET /get/image/{uuid}?thumbnail=true`

### Search (Meilisearch)
- `Pin.document()` returns dict with `id`, `name`, `shops`, `materials`, `tags`, `artists`, `description`.
- Searchable attributes configured on startup.
- Background APScheduler job syncs every N minutes (configurable).
- Manual sync via admin panel (`POST /admin/search/sync`).

### Migrations
- Alembic active. Do **not** use `Base.metadata.create_all()` — write a migration.
- Run: `alembic upgrade head`
- Auto-runs in Docker via `docker-entrypoint.sh`.

### User Pin Lists (Collection, Wants, Trades, Favorites)
Four pin list types: paginated full-list page (`GET /user/{username}/{list}`) + preview strip on profile.

| Section | URL segment | Data source | Description |
|---|---|---|---|
| Favorites | `favorites` | `user_favorite_pins` join table | Pins the user has liked/favorited |
| Collection | `collection` | `UserOwnedPin` | Pins the user owns; per-grade rows with `quantity` and `tradeable_quantity` |
| Want List | `wants` | `UserWantedPin` | Pins the user wants; per-grade rows |
| Trades | `trades` | `UserOwnedPin` filtered by `tradeable_quantity > 0` | Subset of collection available for trade |

**Profile preview:** Each section shows up to 10 pins in a horizontal row (`h-44` flex strip) + `>` see-all card. Counts in section heading.

**Full list pages** (`routes/user/router.py`): Paginated (24/page, distinct pins). Grid/table toggle via `?view=grid|table`. Public.

**Table columns:**
- Favorites: thumbnail, name, shops (links), artists (links)
- Collection: thumbnail, name, shops, artists, grade, qty, tradeable qty
- Wants: thumbnail, name, shops, artists, grade
- Trades: thumbnail, name, shops, artists, grade, tradeable qty

**Key models:**
- `UserOwnedPin` — `user_id`, `pin_id`, `grade_id` (nullable), `quantity`, `tradeable_quantity`. Unique on `(user_id, pin_id, grade_id)`.
- `UserWantedPin` — `user_id`, `pin_id`, `grade_id` (nullable). Unique on `(user_id, pin_id, grade_id)`.

Routes for add/remove/update owned and wanted pins: `routes/user/collection.py` (prefix `/user/pins`).

## Editor Role & Pending Approval System

Editors (`User.is_editor = True`) can create all entity types, but their submissions enter a **pending** state requiring admin approval before becoming publicly visible. Admins have implicit editor privileges; their creations auto-approve.

### PendingMixin (`database/pending_mixin.py`)
Applied to: `Pin`, `Shop`, `Artist`, `Tag`, `Material`, `PinSet`. Adds:
- `approved_at`, `approved_by_id` — set on approval (NULL = pending)
- `rejected_at`, `rejected_by_id` — set on rejection
- Properties: `is_pending`, `is_approved`, `is_rejected`

MRO: `class Pin(PendingMixin, AuditMixin, MappedAsDataclass, Base)`

`PendingAuditEntity` Protocol (same file) — use as the type hint wherever a function needs fields from both `PendingMixin` and `AuditMixin`.

### Visibility rules (enforced in `audit_events._filter_deleted`)
| Viewer | Sees |
|---|---|
| Guest / regular user | Approved items only (`approved_at IS NOT NULL`, `rejected_at IS NULL`) |
| Editor | Approved + pending (`rejected_at IS NULL`) |
| Admin | Same as editor by default; use `include_pending=True` for approval views |

Pending items appear in create/edit form selection lists with a `(P) ` name prefix.

### Auto-approve on admin create
`_before_flush` in `audit_events.py` sets `approved_at`/`approved_by_id` immediately when an admin creates a `PendingMixin` entity. No extra route code needed.

### Edit permissions (`routes/_guards.py`)
`assert_editor_can_edit(entity, current_user)`:
- Admins: always allowed
- Editors: only their own `is_pending` entries (403 otherwise)

### Approval queue (`routes/approve.py`, prefix `/admin/pending`)
| Route | Action |
|---|---|
| `GET /admin/pending` | Queue page — lists all pending entities by type |
| `POST /admin/pending/approve/{type}/{id}` | Approve; cascades to pending deps of a Pin |
| `POST /admin/pending/reject/{type}/{id}` | Mark `rejected_at` (editor can still see/fix) |
| `POST /admin/pending/delete/{type}/{id}` | Soft-delete the pending entry |

**Cascade rule**: approving a Pin also approves any pending shops/artists/materials/tags on that pin — but does NOT bulk-approve other pins that reference those entities.

### Admin management
- `POST /admin/users/{id}/promote-editor` / `demote-editor` — grant/revoke editor role
- Admin panel shows pending count badge; links to `/admin/pending`

## Key Entities
- **Pin** — central model. Has grades, materials, shops, artists, sets, tags, links, images, currency, acquisition/funding type.
- **PinSet** — ordered pin collection. Global (admin) or personal (user). `owner_id` FK.
- **User** — unique username, optional email/password (OAuth users may have no password), `is_admin`, `is_editor`.
- **UserSession** — token (PK), user_id, expires_at.
- **UserAuthProvider** — links User to Google/Discord accounts.
- **UserOwnedPin** — owned pins per-grade with quantity and tradeable quantity.
- **UserWantedPin** — wanted pins per-grade.
- **Artist, Shop, Material, Tag, Grade, Currency, Link** — supporting entities.
- **Tag** — hierarchical (self-referential `parent_id`).

## Deployment (Docker)
The `app` service uses `env_file: .env` so variables from the project `.env` (e.g. `SECRET_KEY`, OAuth) are passed into the container. Values under `environment:` in `docker-compose.yaml` override the same keys from `.env` — so DB URL, Meilisearch URL/key, and `image_directory` stay correct for in-network service names (`postgres`, `meilisearch`).

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

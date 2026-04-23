# PinDB — Claude Code Guide

> **Maintainability note:** Keep this file current. Changes affecting architecture, tech stack, auth, deployment, or structure → update relevant section in the same commit. Only non-obvious things.

## Project Overview
PinDB: FastAPI app for cataloging collectible pins. Server-rendered HTML via **htpy** + **HTMX** (no SPA/REST API), SQLAlchemy ORM over PostgreSQL, Meilisearch full-text search. Session auth: password login + OAuth (Google, Discord, Meta).

## After Every Python Change
Run before task done:
```bash
uvx ruff check --select I --fix .
uvx ruff format .
uvx ty check
```

## Tech Stack
- **Backend:** Python 3.13+, FastAPI, SQLAlchemy 2.0+, Pydantic Settings, APScheduler
- **Auth:** Argon2, DB-backed session tokens, Google OIDC, Discord OAuth, Meta OAuth
- **Frontend:** htpy, HTMX, Tailwind CSS 4, Alpine.js, Tom Select, Lucide icons
- **Database:** PostgreSQL 17, Meilisearch
- **Migrations:** Alembic (runs on container start, not app startup)
- **Tooling:** UV, Ruff, ty
- **CSS build:** Node.js **20+** required (Tailwind v4's `@tailwindcss/oxide` native addon). `npm ci` then `npm run css:build` or `npm run css:watch`. Node 18 fails with "Cannot find native binding".

## Running Locally
```bash
uv sync --all-groups
docker compose -f docker-compose.dev.yaml up -d
alembic upgrade head
fastapi dev ./src/pindb/ --host 0.0.0.0
```

Or: `bash scripts/dev.sh` / `scripts/dev.ps1`

## Project Layout (non-obvious hotspots)

Standard layout: `src/pindb/{database,routes,templates,search,models}/`. Names mirror each other — route `routes/get/pin.py` → template `templates/get/pin.py`. Environment config is Pydantic Settings in `config.py` (source of truth for env vars).

Key files where behaviour isn't obvious from the name:
- `audit_events.py` — session-level SQLAlchemy events (before_flush, after_flush, do_orm_execute). Soft-delete + pending filters live here.
- `auth.py` — FastAPI Depends (`CurrentUser`, `AuthenticatedUser`, `EditorUser`, `AdminUser`) + middleware that threads user into audit ContextVars.
- `routes/_guards.py` — `assert_editor_can_edit()` ownership check.
- `database/joins.py` — all many-to-many association tables (excluded from audit).
- `database/erasure.py` — GDPR account deletion entry point.
- `lifespan.py` — startup: logging, Meili setup, scheduler, admin bootstrap (`_ensure_admins` reads `BOOTSTRAP_ADMIN_USERNAMES`, comma-separated; empty by default).
- `scripts/dump_db.py` — `--via-docker` by default; `POSTGRES_*` env fallback for `--no-via-docker`.

## Audit & History System

Core entities inherit `AuditMixin` (`database/audit_mixin.py`): `created_at/by`, `updated_at/by`, `deleted_at/by`. All fields `init=False` to avoid dataclass field-ordering conflicts — declare as `class Foo(PendingMixin, AuditMixin, MappedAsDataclass, Base)`.

**How it works** (`audit_events.py`, three SQLAlchemy session events):
1. `before_flush` — sets audit timestamps/user_ids; captures diff for ChangeLog; auto-approves `PendingMixin` entities when creator is admin.
2. `after_flush` — writes `ChangeLog` row with JSON patch `{"field": {"old": v, "new": v}}`.
3. `do_orm_execute` — filters soft-deleted + unapproved rows from SELECTs via `with_loader_criteria`.

**Current user** threaded from `attach_user_middleware` → `set_audit_user()` / `set_audit_user_flags()` → ContextVars (`_audit_user_id`, `_audit_user_is_admin`, `_audit_user_is_editor`) → event handlers. No route changes required.

**Soft deletes:** `routes/delete.py` sets `deleted_at`/`deleted_by_id`; never `session.delete()`. Bypass filter with `.execution_options(include_deleted=True)`.

**Pending filter** (same `_filter_deleted`):
| Viewer | Sees |
|---|---|
| Guest / regular user | `approved_at IS NOT NULL` and `rejected_at IS NULL` |
| Editor | Approved + pending (`rejected_at IS NULL`) |
| Admin | Same as editor; `.execution_options(include_pending=True)` for approval views |

Pending items appear in form selection lists with `(P) ` name prefix.

**Excluded from audit:** `UserSession` (ephemeral), all join tables, `ChangeLog` itself.

## Architecture Conventions

### Core
- Routes return HTML, not JSON. HTMX-driven.
- Templates are htpy Python functions returning `htpy.Element`, not Jinja2.
- DB access: `with session_maker() as session:` (read) or `with session_maker.begin() as session:` (write — auto-commits, auto-rollbacks).
- New entity: model in `database/`, router in `routes/`, template in `templates/`. M2M tables in `database/joins.py`.
- Do **not** use `Base.metadata.create_all()` — write an Alembic migration. Run `uv run alembic upgrade head`.

### Sessions & Eager Loading (load-bearing)

Two patterns:

**1. Render inside session (preferred for reads)** — session stays open during `str(template(...))`, lazy relationships work:
```python
with session_maker() as db:
    artist = db.get(Artist, id)
    return HTMLResponse(content=artist_page(request=request, artist=artist))
```

**2. Render outside session (required when write precedes read)** — write block must close first; use `selectinload` for every relationship the template touches:
```python
with session_maker.begin() as db:
    db.execute(...)   # write
with session_maker() as db:
    pin = db.scalar(select(Pin).where(Pin.id == pin_id)
                    .options(selectinload(Pin.shops), selectinload(Pin.artists)))
return HTMLResponse(content=str(template(pin=pin)))
```

**Always `selectinload` on list queries** — prevents N+1 (`artist.pins` in a loop = one query per artist otherwise).

**Columns survive session close; relationships don't.** `pin.name`/`pin.id` safe; `pin.shops` → `DetachedInstanceError`.

### HTMX
- Routes check `request.headers.get("HX-Request")` to return fragments vs full pages.
- `RedirectResponse(..., status_code=303)` for form-to-redirect.
- Authlib stores OAuth state in Starlette `SessionMiddleware` using cookie `pindb_starlette_session` (not `session`, which is the login token).

### Images
- Pin has `front_image_guid` (required), `back_image_guid` (optional) — UUIDs.
- Thumbnails at `{uuid}.thumbnail` (256px WebP), generated eagerly at ingest.
- Two backends (mutually exclusive): `filesystem` or `r2` (Cloudflare R2).
- R2 with `r2_public_url` set → redirects; else proxies bytes. Filesystem → `FileResponse`.
- 20 MB upload limit; EXIF/ICC/XMP stripped on ingest (`_strip_metadata`) to prevent GPS/device leaks.
- Migration: `uv run python scripts/migrate_images.py --direction fs-to-r2|r2-to-fs`

### Search (Meilisearch)
- `Pin.document()` returns the indexed dict.
- Searchable attributes configured on startup.
- APScheduler syncs every N minutes (`search_sync_interval_minutes`, default 5). Manual: `POST /admin/search/sync`.

### Global vs Personal PinSets
- `PinSet.owner_id = NULL` → global/curator set (admin-editable).
- `PinSet.owner_id = {user_id}` → personal set (user-editable).
- Admin can promote personal → global.

## Editor Role & Pending Approval

Editors (`User.is_editor = True`) can create `Pin`, `Shop`, `Artist`, `Tag`, `PinSet`, but submissions enter **pending** state. Admins have implicit editor privileges; their creations auto-approve (via `before_flush`, no route code needed).

`PendingMixin` (`database/pending_mixin.py`) adds `approved_at/by_id`, `rejected_at/by_id`, properties `is_pending`/`is_approved`/`is_rejected`. Use the `PendingAuditEntity` Protocol as the type hint for functions needing both mixins' fields.

Edit permissions (`routes/_guards.py::assert_editor_can_edit`): admins always allowed; editors only on their own `is_pending` entries (403 otherwise).

Approval queue at `/admin/pending` (`routes/approve.py`):
- Approving a Pin cascades to pending shops/artists/tags on *that* pin — but does NOT bulk-approve other pins referencing those entities.
- Rejection sets `rejected_at` (editor can still see/fix).

## User Pin Lists

Four list types, each with a paginated full page (`GET /user/{username}/{list}`) and a 10-item preview strip on the profile.

| Section | URL | Data |
|---|---|---|
| Favorites | `favorites` | `user_favorite_pins` join table |
| Collection | `collection` | `UserOwnedPin` (per-grade; `quantity`, `tradeable_quantity`) |
| Want List | `wants` | `UserWantedPin` (per-grade) |
| Trades | `trades` | `UserOwnedPin` filtered by `tradeable_quantity > 0` |

Full pages paginated 24/page, distinct pins, grid/table toggle via `?view=grid|table`, public.

Add/remove/update routes: `routes/user/collection.py` (prefix `/user/pins`).

`UserOwnedPin` + `UserWantedPin` both unique on `(user_id, pin_id, grade_id)` (grade_id nullable).

## Account Erasure (GDPR)

Entry point: `database/erasure.py::erase_user_account(session, user_id)`.

**Why it uses raw bulk UPDATE/DELETE** (bypassing the ORM audit events): otherwise the old `user_id` would leak back into `change_log.patch` via the audit diff. The erasure itself must NOT be audited against the user being erased.

- Self-service: `POST /user/me/delete-account` (profile Settings modal; must type username to enable submit).
- Admin: `POST /admin/users/{user_id}/delete-account`. Admins cannot delete their own account via admin UI (use self-service or another admin).
- All user-FK columns already nullable with ON DELETE behaviour — no schema migration needed.

## Legal Pages & Footer
- `routes/legal.py` serves `/about`, `/privacy`, `/terms` (public). Templates in `templates/legal/`, shared "not legal advice" banner in `_shared.py`.
- `templates/components/footer.py` rendered by `html_base()` on every full page (not HTMX fragments). Shows version from `pindb.__version__` via `importlib.metadata` and `CONFIGURATION.contact_email`.
- Sticky-footer layout: `body.min-h-screen.flex.flex-col` + `main.flex-grow.min-h-screen`.
- Copyright: project name only ("PinDB"), no person named.

## Key Entities (non-obvious)
- **Pin** — central. Material/finish lives on `Tag` via `TagCategory.material` (no separate entity table).
- **PinSet** — ordered, `owner_id` NULL = global else personal.
- **Tag** — hierarchical via self-referential `parent_id`. Aliases on `tag_aliases`/`shop_aliases`/`artist_aliases` unique per `(entity_id, alias)` — the same alias string may appear on different entities.

## Deployment (Docker)
`app` service uses `env_file: .env`. Values under `environment:` in `docker-compose.yaml` override `.env` keys so DB URL, Meilisearch URL/key, and `image_directory` stay correct for in-network service names (`postgres`, `meilisearch`).

```bash
docker compose up -d                              # Production
docker compose -f docker-compose.dev.yaml up -d   # Dev services only
```

Startup via `docker-entrypoint.sh`: wait for Postgres → `alembic upgrade head` → `uvicorn pindb:app --host 0.0.0.0 --port 8000`.

## Bulk Import
CSV import via `scripts/import_csv.py`. See `scripts/README.md` for column format and grade encoding.

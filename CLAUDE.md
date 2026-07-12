# PinDB — Claude Code Guide

> **Maintainability note:** Keep file current. Changes to architecture, tech stack, auth, deployment, structure → update section in same commit. Only non-obvious things.

## Project Overview
PinDB: FastAPI app cataloging collectible pins. Server-rendered HTML via **htpy** + **HTMX** (no SPA/REST), SQLAlchemy ORM over PostgreSQL, Meilisearch full-text search. Session auth: password + OAuth (Google, Discord, Meta).

## After Every Code Change
Run before task done:
```bash
uvx ruff check --select I --fix .
uvx ruff format .
uvx ty check
npm run js:lint
npm run islands:check   # when frontend/ touched
```

## Tech Stack
- **Backend:** Python 3.13+, FastAPI, SQLAlchemy 2.0+, Pydantic Settings, APScheduler
- **Auth:** Argon2, DB-backed session tokens, Google OIDC, Discord OAuth, Meta OAuth
- **Frontend:** htpy, HTMX, Tailwind CSS 4, Svelte 5 islands (TypeScript), Lucide icons. Alpine.js and Tom Select fully removed — complex widgets are islands; pure show/hide disclosures use the delegated `data-disclosure` pattern in `templates/js/shell/pindb_shell.js`.
- **Select widgets:** all enhanced selects are the native `frontend/lib/MultiSelect.svelte` component (chips, dropdown, remote load via `/get/options/*` or `/bulk/options/*`, create-on-type, tag category branding from `window.TagCategoryData`). Bulk grids use it as a plain component; page forms render a server `<select>` followed by the `multi-select` enhancer island (`island("multi-select", props={"selectId": ...})`), which adopts the select — moves it inside the widget, keeps it synced, dispatches real bubbling `change` events (HTMX `hx-trigger="change"`, form gates and form-persist saves all keep working). Gate check is `pindbSelectHasItems` (reads the underlying select). E2E drives selects only through `tests/e2e/select_helpers.py`, never widget internals. Meilisearch note: index uids all derive from `MEILISEARCH_INDEX` (base name) — `<base>`, `<base>_tags`, `<base>_artists`, `<base>_shops`, `<base>_pin_sets` — so parallel test workers on one Meili server stay isolated; renaming means indexes rebuild on next sync after deploy.
- **Database:** PostgreSQL 17, Meilisearch
- **Migrations:** Alembic (runs on container start, not app startup)
- **Tooling:** UV, Ruff, ty, Oxlint
- **CSS build:** Node.js **20+** required (Tailwind v4 `@tailwindcss/oxide` native addon). `npm ci` then `npm run css:build` or `npm run css:watch`. Node 18 fails with "Cannot find native binding".
- **Lucide (JS):** `npm run build` / `vendor:build` runs `scripts/lucide/build-lucide.mjs` (Rolldown) tree-shakes `lucide` from auto-generated icon list. New dynamic names: add literal in templates or entry in `EXTRA_KEBAB` in that script.
- **Pin image WebP (JS):** `vendor:build` runs `scripts/build-webp-encode.mjs` (Rolldown + `@jsquash/webp`) → `static/vendor/pindb-webp/` (ESM + `.wasm`). Pin create/edit and bulk pin import load it for optional client-side WebP before upload.

## Running Locally
```bash
uv sync --all-groups
docker compose -f docker-compose.dev.yaml up -d
alembic upgrade head
fastapi dev ./src/pindb/ --host 0.0.0.0
```

Or: `bash scripts/dev.sh` / `scripts/dev.ps1`

## Project Layout (non-obvious hotspots)

Standard layout: `src/pindb/{database,routes,templates,search,models}/`. Names mirror — route `routes/get/pin.py` → template `templates/get/pin.py`. Env config = Pydantic Settings in `config.py` (source of truth for env vars).

**Svelte islands** (complex interactive widgets; htpy + HTMX stay for pages/fragments): source in `frontend/` at repo root (TypeScript + Svelte 5 runes; never imported by Python). `npm run islands:build` (or `islands:watch` during dev, alongside `fastapi dev`) emits to gitignored `src/pindb/static/islands/` — stable entry names + content-hashed shared chunks; `vite.config.ts` auto-globs `frontend/islands/*.entry.ts` (each entry = 2 lines via `lib/define-island.ts`). Templates render mount points via `island("name", props={...})` from `templates/components/islands.py` (props = real JSON script block — never `json.dumps().replace('"', "'")`); loader (`frontend/mount.ts`, loaded in `base.py`) mounts on load + `htmx:afterSwap`/`oobAfterSwap`/`historyRestore`, unmounts on `htmx:beforeCleanupElement`. Rules: Tailwind classes only, literal strings, no `<style>` blocks (`input.css` has `@source` for `frontend/`); icons via `@lucide/svelte` direct imports; shared reactive modules named `*.svelte.ts`; islands never rely on legacy scripts binding listeners into their DOM (mount is async — interop via localStorage/CustomEvents/self-applied effects). `npm run islands:check` (svelte-check) gates components; oxlint skips `.svelte`. `preserveEntrySignatures: "exports-only"` in `vite.config.ts` keeps island default exports — do not remove. E2E visual parity: `assert_screenshot` fixture + `tests/e2e/screenshots.py`; baselines in `tests/e2e/__screenshots__/` are machine-specific — regenerate via `uv run pytest -m e2e --update-screenshots` and visually review before committing.

First-party page scripts live under `templates/js/` in subfolders (`shell/`, `forms/`, `tags/`, `pins/`, `shared/`). Mount stays `/templates-js/` with `CacheBustedTemplateJsFiles` (same long cache as vendored static); use `templates_js_url("pins/pin_lightbox.js")` so every URL includes `?v=<process start>` (see `templates/base.py` and `template_js_extra` on pages). `html_base` always loads `forms/htmx_submit_guard.js`; opt in per form with `data-htmx-submit-guard` to disable submit + spinner during HTMX posts (create/edit flows).

Key files where behavior not obvious from name:
- `audit_events.py` — session-level SQLAlchemy events (before_flush, after_flush, do_orm_execute). Soft-delete + pending filters here.
- `auth.py` — FastAPI Depends (`CurrentUser`, `AuthenticatedUser`, `EditorUser`, `AdminUser`) + middleware threads user into audit ContextVars.
- `routes/_guards.py` — `assert_editor_can_edit()` ownership check.
- `database/joins.py` — all M2M association tables (excluded from audit).
- `database/erasure.py` — GDPR account deletion entry.
- `lifespan.py` — startup: logging, Meili setup, scheduler, admin bootstrap (`_ensure_admins` reads `BOOTSTRAP_ADMIN_USERNAMES`, comma-separated; empty default).
- `scripts/dump_db.py` — `--via-docker` default; `POSTGRES_*` env fallback for `--no-via-docker`.

## Audit & History System

Core entities inherit `AuditMixin` (`database/audit_mixin.py`): `created_at/by`, `updated_at/by`, `deleted_at/by`. All fields `init=False` to avoid dataclass field-ordering conflicts — declare as `class Foo(PendingMixin, AuditMixin, MappedAsDataclass, Base)`.

**How works** (`audit_events.py`, three SQLAlchemy session events):
1. `before_flush` — sets audit timestamps/user_ids; captures diff for ChangeLog; auto-approves `PendingMixin` entities when creator is admin.
2. `after_flush` — writes `ChangeLog` row with JSON patch `{"field": {"old": v, "new": v}}`.
3. `do_orm_execute` — filters soft-deleted + unapproved rows from SELECTs via `with_loader_criteria`.

**Current user** threaded `attach_user_middleware` → `set_audit_user()` / `set_audit_user_flags()` → ContextVars (`_audit_user_id`, `_audit_user_is_admin`, `_audit_user_is_editor`) → event handlers. No route changes needed.

**Soft deletes:** `routes/delete.py` sets `deleted_at`/`deleted_by_id`; never `session.delete()`. Bypass filter: `.execution_options(include_deleted=True)`.

**Pending filter** (same `_filter_deleted`):
| Viewer | Sees |
|---|---|
| Guest / regular user | `approved_at IS NOT NULL` and `rejected_at IS NULL` |
| Editor | Every review state — approved + pending + needs-changes (no predicate at all) |
| Admin | Same as editor; `.execution_options(include_pending=True)` for approval views |

Needs-changes rows stay visible to editors on purpose: the submitter has to read the feedback and fix the entry. Hiding them makes the change request impossible to act on.

Review-state markers in selection lists/headings come from `utils.py::review_label` — `(P) ` pending, `(C) ` needs-changes. Meili documents carry `is_pending`/`is_rejected` so `search_entity_options` can prefix without a DB roundtrip.

**Excluded from audit:** `UserSession` (ephemeral), all join tables, `ChangeLog` itself.

## Architecture Conventions

### Core
- Routes return HTML, not JSON. HTMX-driven.
- Templates = htpy Python functions returning `htpy.Element`, not Jinja2.
- DB access: `with session_maker() as session:` (read) or `with session_maker.begin() as session:` (write — auto-commits, auto-rollbacks).
- New entity: model in `database/`, router in `routes/`, template in `templates/`. M2M tables in `database/joins.py`.
- Do **not** use `Base.metadata.create_all()` — write Alembic migration. Run `uv run alembic upgrade head`.

### Sessions & Eager Loading (load-bearing)

Two patterns:

**1. Render inside session (preferred for reads)** — session stays open during `str(template(...))`, lazy relationships work:
```python
with session_maker() as db:
    artist = db.get(Artist, id)
    return HTMLResponse(content=artist_page(request=request, artist=artist))
```

**2. Render outside session (required when write precedes read)** — write block must close first; use `selectinload` for every relationship template touches:
```python
with session_maker.begin() as db:
    db.execute(...)   # write
with session_maker() as db:
    pin = db.scalar(select(Pin).where(Pin.id == pin_id)
                    .options(selectinload(Pin.shops), selectinload(Pin.artists)))
return HTMLResponse(content=str(template(pin=pin)))
```

**Always `selectinload` on list queries** — prevents N+1 (`artist.pins` in loop = one query per artist otherwise).

**Columns survive session close; relationships don't.** `pin.name`/`pin.id` safe; `pin.shops` → `DetachedInstanceError`.

### HTMX
- Routes check `request.headers.get("HX-Request")` to return fragments vs full pages.
- `RedirectResponse(..., status_code=303)` for form-to-redirect.
- Authlib stores OAuth state in Starlette `SessionMiddleware` using cookie `pindb_starlette_session` (not `session`, which is login token).

### Images
- Pin has `front_image_guid` (required), `back_image_guid` (optional) — UUIDs.
- Thumbnails: objects `{uuid}.thumb.{w}` for `w ∈ {50, 100, 200, 400, 600}` (WebP, long-edge fit), generated eagerly at ingest. Legacy data may still have `{uuid}.thumbnail` (256px WebP); `GET /get/image/{guid}?thumbnail=true` prefers `.thumb.200` then falls back to `.thumbnail`.
- `GET /get/image/{guid}?w=N` serves a sized thumb when `N` is in that set. Templates use `pin_thumbnail_img()`: `src` is the smallest stored width (fallback), `srcset` lists all widths with `w` descriptors, `sizes` is a comma-separated media-query list (first match wins) per layout.
- Two backends (mutually exclusive): `filesystem` or `r2` (Cloudflare R2).
- R2 with `r2_public_url` set → redirects; else proxies bytes. Filesystem → `FileResponse`.
- 20 MB upload limit; EXIF/ICC/XMP stripped on ingest (`_strip_metadata`) prevents GPS/device leaks.
- Migration: `uv run python scripts/migrate_images.py --direction fs-to-r2|r2-to-fs`

### Search (Meilisearch)
- `Pin.document()` returns indexed dict.
- Searchable attributes configured on startup.
- APScheduler syncs every N minutes (`search_sync_interval_minutes`, default 5). Manual: `POST /admin/search/sync`.
- **DB ↔ Meili sync rule:** Every write that changes entity visibility or content must be followed by a Meili call. Use `sync_entity(entity_type, entity_id)` (upsert or auto-delete if gone) or `delete_one(entity_type, id)` (immediate remove). For pin approval with cascade, use `sync_pin_with_deps(pin_id)` which also re-syncs the pin's shops/artists/tags. Applies to: create, direct edit, approve, reject, delete — for all five tracked entity types (Pin, Tag, Artist, Shop, PinSet). Call **after** the write session closes.

### Achievements & User Stats
- `achievements.py` = derived-state sync layer (like `search/update.py`). `UserStats` (wide row per user) is always **recomputed from source**, never incremented; `UserAchievement` rows are permanent (unique on `(user_id, family, tier)` — that constraint is the exactly-once award mechanism; the winning `ON CONFLICT DO NOTHING ... RETURNING` insert also creates the notification `Message` in the same transaction).
- **Stats sync rule (mirrors the Meili rule):** every write that changes a user's countable contributions (create/edit/approve/reject/delete of Pin/Tag/Shop/Artist/PinSet, favorites, owned/wanted) is followed by `await refresh_user_stats(user_id)` (or `refresh_users_stats([...])` for multi-user approval flows) **after** the write session closes, beside the existing `sync_entity` call. It never raises (logs instead); the hourly scheduler sweep (`stats_refresh_interval_minutes`) self-heals missed call sites.
- Edit stats union `ChangeLog` (`operation="update"`) with **approved** `PendingEdit` rows — the ChangeLog row for an applied pending edit credits the approving admin, so PendingEdit is the editor's paper trail. "Others' entities" predicates use `IS DISTINCT FROM` (erasure nulls `created_by_id`).
- Badge UI: `templates/components/achievements/badge.py`; colors = `achievement-*`/`metal-*` tokens in `input.css` (tag-chip exception pattern); metal border shine = scroll-driven animation (`animation-timeline: view()`, static fallback). Badge icons load via `EXTRA_KEBAB` in `build-lucide.mjs` (dict-lookup icons are invisible to the scanner).

### Global vs Personal PinSets
- `PinSet.owner_id = NULL` → global/curator set (admin-editable).
- `PinSet.owner_id = {user_id}` → personal set (user-editable).
- Admin can promote personal → global.

## Editor Role & Pending Approval

Editors (`User.is_editor = True`) can create `Pin`, `Shop`, `Artist`, `Tag`, `PinSet`, but submissions enter **pending** state. Admins have implicit editor privileges; their creations auto-approve (via `before_flush`, no route code needed).

`PendingMixin` (`database/pending_mixin.py`) adds `approved_at/by_id`, `rejected_at/by_id`, properties `is_pending`/`is_approved`/`is_rejected`. Use `PendingAuditEntity` Protocol as type hint for functions needing both mixins' fields.

Edit permissions (`routes/_guards.py::assert_editor_can_edit`): admins always allowed; editors only on own `is_pending` entries (403 otherwise).

Approval queue at `/admin/pending` (`routes/approve.py`):
- Approving Pin cascades to pending shops/artists/tags on *that* pin — does NOT bulk-approve other pins referencing those entities.

### Needs Changes (the third review state)

**DB `rejected_*` ≡ UI "Needs Changes".** The columns kept their original names (renaming is unsafe under blue/green); everything user-facing says "Needs Changes", and the admin button says *Request changes*. Not a terminal state — it is a review conversation.

- **Reason is mandatory.** All three reject routes (`/reject`, `/reject-edits`, `/reject-bulk`) take a `reason` form field, validated `>= MIN_CHANGE_REQUEST_LENGTH` (25, in `database/pending_mixin.py`) after `.strip()`. The client-side gate is the `request-changes-modal` island; the route check is the real one.
- The reason is stored on the entity/edit (`rejection_reason`) **and** sent to the submitter as a `Message` (`MessageCategory.changes_requested`, `ChangesRequestedBody`). The column is current state; the message is the notification. Both — the editor may archive the message, and the queue/banner need the reason without joining `messages`.
- **Editing clears the flag** (`_guards.py::clear_rejection_on_resubmit`, called from the direct-edit branch of `routes/edit/*`), returning the entry to Pending. An admin editing a flagged entry does *not* clear it.
- **Edit chains:** `get_edit_chain`/`get_head_edit` include needs-changes edits — a flagged edit is still the tip of the chain, so the edit form prefills from it, a resubmission stacks on it (`reopen_rejected_edits`), and approving a flagged chain applies it. Only the queue's own section queries split pending (`rejected_at IS NULL`) from needs-changes (`IS NOT NULL`).
- **Meili:** reject calls `sync_entity`, **not** `delete_one` — needs-changes entries stay indexed like pending ones so the editor can find them. Meili is only an id source; the ORM filter is the visibility gate.
- **No stats refresh on reject:** only approved entries count, and an entry only reaches needs-changes from pending.
- The nav/heading pending counts exclude needs-changes (`routes/admin/_pending_count.py`) — those entries are waiting on their submitter, not on an admin.

Wire value note: `MessageCategory.changes_requested` deliberately persists as `"pin_rejection"` — `messages.category` is `VARCHAR(13)` sized to it, and the SQLAlchemy `Enum` uses `values_callable` to store `.value` rather than the member name. Renaming the member alone would have written an 17-char string into a 13-char column.

## User Pin Lists

Four list types, each with paginated full page (`GET /user/{username}/{list}`) and 10-item preview strip on profile.

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

Entry: `database/erasure.py::erase_user_account(session, user_id)`.

**Why raw bulk UPDATE/DELETE** (bypasses ORM audit events): otherwise old `user_id` leaks back into `change_log.patch` via audit diff. Erasure itself must NOT be audited against user being erased.

- Self-service: `POST /user/me/delete-account` (profile Settings modal; must type username to enable submit).
- Admin: `POST /admin/users/{user_id}/delete-account`. Admins cannot delete own account via admin UI (use self-service or another admin).
- All user-FK columns already nullable with ON DELETE behavior — no schema migration needed.

## Legal Pages & Footer
- `routes/legal.py` serves `/about`, `/privacy`, `/terms` (public). Templates in `templates/legal/`, shared "not legal advice" banner in `_shared.py`.
- `templates/components/shell/footer.py` rendered by `html_base()` on every full page (not HTMX fragments). Shows version from `pindb.__version__` via `importlib.metadata` and `CONFIGURATION.contact_email`.
- Sticky-footer layout: `body.min-h-screen.flex.flex-col` + `main.flex-grow.min-h-screen`.
- Copyright: project name only ("PinDB"), no person named.

## Key Entities (non-obvious)
- **Pin** — central. Material/finish lives on `Tag` via `TagCategory.material` (no separate entity table).
- **PinSet** — ordered, `owner_id` NULL = global else personal.
- **Tag** — hierarchical via self-referential `parent_id`. Aliases on `tag_aliases`/`shop_aliases`/`artist_aliases` unique per `(entity_id, alias)` — same alias string may appear on different entities.

## Deployment (Docker)

App services use `env_file: .env`. Values under `environment:` in `docker-compose.yaml` override `.env` keys so DB URL, Meilisearch URL/key, `image_directory` stay correct for in-network service names (`postgres`, `meilisearch`).

Production image multi-stage: Node asset stage copies `scripts/` and runs
`npm run build` (`css:build` + `vendor:build` + Rolldown Lucide), copies
generated `main.css` plus vendored frontend assets into Python runtime image.
Fresh CI checkouts won't have generated files unless they run frontend build or build Docker image.

### Architecture (zero-downtime blue/green)

```
NPM (separate stack) -> host:8000 -> proxy (Caddy) -> app_blue:8000  (one of
                                                  └─ app_green:8000   the two)
                                                  scheduler (1 replica, no HTTP)
```

- `app_blue` / `app_green` — identical web service under compose `profiles: ["blue"]` / `["green"]`. Only one runs normally; both up briefly during deploy swap. Neither publishes host port.
- `proxy` — Caddy. Binds host `:8000` (port NPM already targets). Lists both colors as upstreams with active `/healthz` checks; routes only to healthy ones.
- `scheduler` — single replica, no uvicorn. Owns APScheduler + recurring Meili sync, gated by `ENABLE_SCHEDULER=true`. Web containers set `ENABLE_SCHEDULER=false` so duplicate jobs never fire when both colors up.
- `migrate` — one-shot service under `profiles: ["migrate"]`. Runs `alembic upgrade head` once per deploy; app entrypoint no longer migrates.

`/healthz` (`src/pindb/routes/health.py`) = public no-DB liveness probe; both Caddy load-balancer healthcheck and Docker `HEALTHCHECK` use it.

### Daily deploy

```bash
./scripts/deploy.sh
```

Builds **app_blue, app_green, migrate, scheduler** (each Compose service gets own image tag — building only app colors leaves `migrate` stale so Alembic misses new revisions), runs migrations, starts idle color, waits for healthy, stops old color, restarts scheduler. Aborts without killing live color if new one fails healthcheck. State (which color live) in `.deploy-active-color` — gitignored, host-local, default `blue`.

### Bootstrap (first time only — has ~5–15s of NPM 502s)

```bash
./scripts/bootstrap.sh
```

Validates `.env`, builds, releases host:8000 from any legacy single-`app` container, brings up postgres + meili (waits for healthy), runs migrations, starts active color (default `blue`), then `scheduler` + `proxy`. Idempotent — safe to re-run.

### Restart hardening

All long-lived services use `restart: unless-stopped`. Docker daemon restarts every container running before shutdown when boots, so host reboot brings stack back automatically — no extra wiring.

Two prerequisites:
- Docker daemon must start on boot: `sudo systemctl enable docker` (bootstrap warns if not enabled).
- Containers must have been running (not manually `stop`'d) before reboot.

For belt-and-suspenders / explicit systemctl control, install optional unit:

```bash
sudo cp scripts/pindb.service /etc/systemd/system/pindb.service
sudo sed -i "s|@WORKDIR@|$(pwd)|; s|@USER@|$(whoami)|" /etc/systemd/system/pindb.service
sudo systemctl daemon-reload && sudo systemctl enable --now pindb.service
```

Unit calls `scripts/start.sh`, reads `.deploy-active-color`, runs `compose up -d` for postgres, meili, active color, scheduler, proxy. Useful after `docker compose down` or container pruning.

### Dev services

```bash
docker compose -f docker-compose.dev.yaml up -d   # Postgres + Meili only
```

### Migration discipline (load-bearing)

During swap, old + new app containers run against same DB simultaneously ~10–30s. Alembic revisions must be both forward- AND backward-compatible:

- **Safe:** add nullable column, add table, add index `CONCURRENTLY`, backfill data, add enum value.
- **Unsafe same-release:** `DROP COLUMN` still read by old code, `ALTER COLUMN ... NOT NULL` on column old code leaves NULL, rename column/table, incompatible type change, remove enum value.
- **Split unsafe changes across two deploys:** (1) add new col nullable, dual-write. (2) backfill, flip reads. (3) drop old col.

Container startup: `docker-entrypoint.sh` now just `uvicorn pindb:app --host 0.0.0.0 --port 8000 --proxy-headers`. Migrations belong in `compose run --rm migrate`, never entrypoint (would race during blue/green overlap).

## Bulk Import
CSV import via `scripts/import_csv.py`. See `scripts/README.md` for column format and grade encoding.

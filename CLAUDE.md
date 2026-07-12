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
- **Migrations:** Alembic (one-shot `migrate` compose service, once per deploy — not container start, not app startup)
- **Tooling:** UV, Ruff, ty, Oxlint
- **CSS build:** Node.js **20+** required (Tailwind v4 `@tailwindcss/oxide` native addon). `npm ci` then `npm run css:build` or `npm run css:watch`. Node 18 fails with "Cannot find native binding".
- **Icon color inheritance (load-bearing, `input.css` `@layer base`):** the default text color is set on `html` and **must never** be reasserted as `* { color: … }`. A universal `color` declaration matches every element, and a matched declaration beats inheritance, so `color` stops cascading entirely — a Lucide `<svg>` (and each `<path>` it strokes with `currentColor`) then resolves `currentColor` against its *own* base-text color, not the colored button/banner/chip around it, and **every icon everywhere renders base text**. `color: inherit` on the svg alone doesn't rescue it: the plain `<div>`/`<span>` between icon and colored ancestor is pinned to base-text by the same rule. Elements the UA colors itself (`a`, form controls, `svg`) are reset to `color: inherit` there — that reset is what the old `*` rule was really buying. To give an icon a color that differs from its container, put a `text-*` utility on the icon (utilities layer beats base) or use a component class rule; do not add per-component `color: inherit` patches (`.btn`, `.theme-appearance-icon` used to carry one each).
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

**How works** (`audit_events.py`, five SQLAlchemy session events):
1. `before_flush` — sets audit timestamps/user_ids; captures diff for ChangeLog; auto-approves `PendingMixin` entities when creator is admin.
2. `after_flush` — writes `ChangeLog` row with JSON patch `{"field": {"old": v, "new": v}}`.
3. `do_orm_execute` — filters soft-deleted + unapproved rows from SELECTs via `with_loader_criteria`.
4. `after_rollback` / `after_soft_rollback` — `_discard_pending_audit` drops the entries `before_flush` queued. Without it a rolled-back flush leaves the queue populated and the next successful flush writes ChangeLog rows for changes that never landed.

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

**Excluded from audit:** `UserSession` (ephemeral), all join tables, `ChangeLog` itself, `ContentReport` (carries no `AuditMixin` at all). `Message`, `UserDisplay` and `UserDisplayImage` keep the audit timestamps but set `__change_log_exclude__` — their content is personal and would otherwise be copied into `change_log.patch`, where it outlives erasure.

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

**Never `selectinload(X.pins)` to feed an entity list card** (`database/pin_previews.py`). Tag/shop/artist/pin-set cards show a pin count and four thumbnails; eager-loading the relationship to get them hydrates every attached `Pin` — 60k ORM objects to draw 400 images on a 100-entity page. Routes call `load_pin_previews(...)` and templates take `previews.count(id)` / `previews.pins(id)`; `entity_grid_card` and `thumbnail_grid` take an explicit `pin_count` and a pre-sampled `pins` list, and never call `len()` on a relationship.

**The pin count is viewer-dependent, so it cannot be denormalized onto a column.** `_filter_deleted` hides soft-deleted rows from everyone and unapproved ones from non-editors, so the same tag legitimately shows a different count to a guest and to an editor. `load_pin_previews` selects `Pin` as a mapped entity precisely so that filter applies to its queries too (covered by `tests/integration/test_pin_previews.py`).

**Every pin-facing join table is indexed on its non-pin column** (`ix_pins_tags_tag_id` and friends, declared in `database/joins.py`). The composite PK leads with `pin_id`, so it cannot serve the "which pins belong to this tag" direction that every list page, detail page, and preview loader asks — without these it is a sequential scan of the whole join table. A correlated `COUNT(*)` over a join table to answer "does this entity have any pins" is likewise a scan-per-row: use `EXISTS`, which the index answers as an index-only probe.

### Rendering responses (load-bearing on big pages)

**On a page with many components, render with `HTMLResponse(content=str(template(...)))`, not `HtpyResponse(template(...))`.** `HtpyResponse` streams the element tree node by node; a 100-card list page is tens of thousands of async chunk yields pumped through anyio memory streams and the middleware stack, which measured **~4x the cost of just building the string** (`/list/tags` 435ms → 61ms). It also renders *lazily* — after the route returns and its `async with session_maker()` block has closed — so any relationship the template touches raises `DetachedInstanceError`; `str()` inside the session block does not. `routes/list/_render.py` and every `get/*` page render this way. `HtpyResponse` stays fine for small fragments.

**`request.url_for` is a reverse lookup over every route in the app** — not a string format, and ~180x slower than one. Never call it in a per-item loop. `templates/components/pins/pin_thumbnail.py` was calling it 6x per image (src + 5 `srcset` widths) — ~1450 lookups and ~150ms on one list page; it now resolves the route once per request, caches `(prefix, suffix)` on `request.state`, and interpolates. `tests/unit/test_pin_thumbnail_srcset.py` asserts the output stays byte-identical to `url_for` — that assertion is what makes the shortcut safe if the route ever moves.

### HTMX
- Routes check `request.headers.get("HX-Request")` to return fragments vs full pages.
- `RedirectResponse(..., status_code=303)` for form-to-redirect.
- Authlib stores OAuth state in Starlette `SessionMiddleware` using cookie `pindb_starlette_session` (not `session`, which is login token).

### Images
- Pin has `front_image_guid` (required), `back_image_guid` (optional) — UUIDs.
- Thumbnails: objects `{uuid}.thumb.{w}` for `w ∈ {50, 100, 200, 400, 600}` (WebP, long-edge fit), generated eagerly at ingest. Legacy data may still have `{uuid}.thumbnail` (256px WebP); `GET /get/image/{guid}?thumbnail=true` prefers `.thumb.200` then falls back to `.thumbnail`.
- `GET /get/image/{guid}?w=N` serves a sized thumb when `N` is in that set. Templates use `pin_thumbnail_img()`: `src` is the smallest stored width (fallback), `srcset` lists all widths with `w` descriptors, `sizes` is a comma-separated media-query list (first match wins) per layout.
- `file_handler.delete_image(guid)` irreversibly removes the original **and all five thumbs**. Only account erasure calls it — see "User Displays". Ordinary deletes soft-delete the row and leave the bytes.
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
- The same three actions also sit on an unapproved entry's **detail page** for admins (`review_actions_bar`, `templates/components/display/review_actions.py`, rendered by all five `templates/get/*` pages) — an admin who opens a submission to look at it can rule on it there. They post to the same `/admin/pending/{approve,reject,delete}/…` routes with **`?after=back`**, which answers `204` + `HX-Trigger: pindb:review-action-done` instead of the `#pending-content` fragment; the shell (`templates/js/shell/pindb_shell.js`) walks the admin one step back in history and flags a reload so the page they land on isn't restored stale from the bfcache. Needs-changes entries get Approve + Delete only, mirroring the queue's own section.
- While that bar is up, the heading's own Delete icon is suppressed: `/delete/{entity_type}/{id}` uses a plain `session.get` with no `include_pending`, so it cannot see an unapproved row at all — two Deletes, one of them a silent no-op.

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

## User Displays

Photos of a user's *real-life* pin display, at the shareable public page `GET /user/{username}/display`. The point is organic promotion: the link unfurls in Discord with the user's cover photo plus PinDB branding, and the "Pins in this display" strip carries the click back into the catalog. Everything lives in `routes/user/displays.py` + `templates/user/display_{page,edit,layouts}.py` + the `display-editor` island.

- **`UserDisplay` is 1:1 with a user, created lazily** (`_get_or_create_display`, `pg_insert ... ON CONFLICT DO NOTHING` on the unique `user_id`) — not at signup, or every account that never uses the feature leaves a dead row. **The cover photo is simply the image at the lowest `position`**; there is no `cover_image_id` (it would be a circular FK needing a fixup on every cover delete).
- **A user with no display is a 200 empty state, never a 404** — a shared link must not break.
- **Route ordering trap:** `/user/me/display/edit` and `/user/{username}/display` are the same shape, so `me` matches `{username}`. The `/me/...` routes are declared first *within* `displays.py`, and the router is included before `router.py`'s `/{username}` catch-all. Get it wrong and every owner route 404s with "User not found" — a routing bug that reads like a template bug.
- **The pin picker has its own options endpoint** (`GET /user/me/display/pin-options`). `/get/options/{entity_type}` is `require_editor`-gated on purpose (it reads Meili with no ORM re-hydration and would leak pending entities), so a regular user tagging pins in their own photo would get a 403 from it. This one goes through `search_pin`, which re-hydrates via the ORM so `_filter_deleted` applies.
- **`pin_ids` is `list[str]`, not `list[int]`.** An empty list serializes to *no form field at all*, so an int list cannot distinguish "don't touch the pins" from "remove them all" — both arrive absent, and untagging the last pin silently no-ops. The client sends a single empty string to mean *explicitly none*.
- **Layouts** (`display_layouts.py`): `collage` / `grid` / `vertical` / `carousel`, plus a per-image `feature` size hint = span-2. Collage is a CSS **grid** with `grid-flow-dense`, not columns-masonry — multi-column CSS cannot span an item across columns, and the feature hint is a requirement. `auto-rows-[...]` is load-bearing: without an explicit row height `row-span-2` means nothing. In the fixed-height cover layouts the caption is **overlaid on the photo** (a below-image caption spills out of its cell); `vertical` keeps it below.
- **Enum columns pass `length=32` explicitly.** `native_enum=False` otherwise sizes the VARCHAR to the longest value that exists *today* (`"carousel"` → `VARCHAR(8)`), so the next layout anyone adds needs a migration to widen it. This is the `messages.category` `VARCHAR(13)` story, pre-empted.
- **`UserDisplay`/`UserDisplayImage` set `__change_log_exclude__`** (like `Message`): the audit diff would otherwise copy captions, titles and image guids into `change_log.patch`, where they survive account erasure.
- **Erasure hard-deletes the photos *and their bytes*.** `erase_user_account` returns the orphaned guids and the caller passes them to `file_handler.delete_image` **after the transaction commits** (blob deletion is irreversible; a rollback would otherwise leave rows pointing at bytes that are gone). Pin art is different — it belongs to catalog pins that outlive the account — but a display photo is a picture of someone's home and nothing else references it. The per-image delete route only *soft*-deletes and leaves the bytes.
- **No Meili sync and no `refresh_user_stats`.** Displays are not a tracked entity type, and a photo of your own shelf is not a contribution to the catalog. Don't "fix" the omissions.
- **Share card:** `og_image.py::build_user_display_og_image` (route branch `user_display` in `routes/get/og_image.py`, keyed on **user id**). The cover photo is cover-fit full-bleed under two scrims — a flat wash plus a bottom gradient — with the wordmark *drawn as text*, since the `opengraph-image-blank.webp` asset has it baked into an opaque background and cannot be layered over a photo. It loads the **original**, not a 600px thumb: the pin card contain-fits a small image, but this one scales a photo up to a 1200px frame. No photos → falls back to the blank-template card.

## Content Reports

`ContentReport` (`database/content_report.py`) is a generic `(target_type, target_id)` report → `/admin/reports` queue (`routes/admin/reports.py`). Only `display_image` is wired up today; the enum carries the rest so pins/tags extend without a schema change. Filing requires a signed-in account; `UniqueConstraint(reporter_id, target_type, target_id)` absorbs duplicate reports via `ON CONFLICT DO NOTHING` rather than 500ing.

**The pointer has no foreign key.** Nothing cascades, and no FK check will ever remind you. So: every path that deletes a reportable row must close the reports naming it (erasure deletes them; the admin "Remove content" action marks *every* open report on that target `actioned`), and the queue must render when a target has already vanished. Reports a user *filed* survive their account erasure, anonymised — `reporter_id` is nullable precisely for that.

`ContentReport` carries no `AuditMixin` (so it is excluded from audit like `ChangeLog`) and its `created_at` has a `server_default` — it is written by a Core `ON CONFLICT` insert, which bypasses the ORM's `default_factory` entirely. Same reason `MessageReceipt` has one.

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
- Sticky-footer layout: `body.min-h-screen.flex.flex-col` + `main.min-h-screen.relative.z-5` (`templates/base.py`).
- Copyright: project name only ("PinDB"), no person named.

## Key Entities (non-obvious)
- **Pin** — central. Material/finish lives on `Tag` via `TagCategory.material` (no separate entity table).
- **PinSet** — ordered, `owner_id` NULL = global else personal.
- **Tag** — hierarchical via self-referential `parent_id`. Aliases on `tag_aliases`/`shop_aliases`/`artist_aliases` unique per `(entity_id, alias)` — same alias string may appear on different entities.

## Deployment (Docker)

App services use `env_file: .env`. Values under `environment:` in `docker-compose.yaml` override `.env` keys so DB URL, Meilisearch URL/key, `image_directory` stay correct for in-network service names (`postgres`, `meilisearch`).

**The image is built in CI, not on the host.** `.github/workflows/release.yml` builds and pushes `ghcr.io/joshuamaddy/pindb` on every push to `main` (tags: `latest`, `sha-<full-sha>`, branch name, and `v*` git tags). All four app services — `app_blue`, `app_green`, `migrate`, `scheduler` — share **one** image via the `x-app-image` YAML anchor, pinned to `ghcr.io/joshuamaddy/pindb:${IMAGE_TAG:-latest}`. `deploy.sh` and `bootstrap.sh` `docker compose pull` it; neither builds. So a host deploy only picks up code that has landed on `main` **and** finished its Release run — `git pull` on the host refreshes compose/Caddyfile/scripts, *not* the app.

One image for every service is what keeps `migrate` from going stale: Alembic runs from the same build as the web containers, so it can never miss a revision they expect.

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

Pulls `ghcr.io/joshuamaddy/pindb:${IMAGE_TAG:-latest}`, runs migrations (`migrate` profile), starts idle color, waits for healthy, smoke-tests `/healthz` through Caddy, stops old color, restarts scheduler. Aborts without killing live color if new one fails healthcheck. State (which color live) in `.deploy-active-color` — gitignored, host-local, default `blue`.

**Rollback / pinning:** `IMAGE_TAG` selects what gets pulled, so any past build is one deploy away — `IMAGE_TAG=sha-<full-sha> ./scripts/deploy.sh`. Note this rolls back *code only*; a migration already applied stays applied, which is exactly why the migration-discipline rules below are load-bearing.

### Bootstrap (first time only — has ~5–15s of NPM 502s)

```bash
./scripts/bootstrap.sh
```

Validates `.env`, pulls the image from ghcr.io (`docker login ghcr.io` first if the package is private), releases host:8000 from any legacy single-`app` container, brings up postgres + meili (waits for healthy), runs migrations, starts active color (default `blue`), then `scheduler` + `proxy`. Idempotent — safe to re-run.

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

Container startup: `docker-entrypoint.sh` now just `uvicorn pindb:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'`. Migrations belong in `compose run --rm migrate`, never entrypoint (would race during blue/green overlap).

The `migrate` service overrides `entrypoint:` with the full `alembic upgrade head` argv, so trailing args are *appended to that command*, not substituted for it. Any other Alembic command needs the entrypoint replaced:

```bash
docker compose --profile migrate run --rm --entrypoint /app/.venv/bin/python migrate -m alembic current
```

## Bulk Import
In-app, admin-only: `GET /bulk/pin` (grid editor, `bulk-import` island) → `POST /bulk/pin/image` per image → `POST /bulk/pin` with the rows as JSON (`routes/bulk/pin.py`). Entity cells resolve through `/bulk/options/{entity_type}` and `_get_or_create`, so a typed-in shop/tag/artist is created inline.

The old `scripts/import_csv.py` CSV importer no longer exists; `scripts/README.md` documents its format for reference only (a `scripts/import.csv` and `scripts/Images/` still sit in the tree).

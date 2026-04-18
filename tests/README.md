# PinDB test suite

The suite is organised into three layers that trade fidelity for speed:

| Layer | Directory | Marker | External deps | Typical run time |
|---|---|---|---|---|
| Unit | `tests/unit/` | `unit` | none | <1 s |
| Integration | `tests/integration/` | `integration` | Postgres (testcontainers) | 15–90 s |
| End-to-end | `tests/e2e/` | `e2e` | Postgres + Meilisearch (testcontainers), Playwright browser, real uvicorn | 1–5 min |

By default `pyproject.toml` sets `-m "not e2e"`, so `uv run pytest` runs only unit + integration.

## Running the layers

### Unit only
```bash
uv run pytest tests/unit/ -q
```

### Integration (default set + unit)
```bash
uv run pytest
```
Requires Docker (for the Postgres testcontainer). Each test runs inside a
transaction that is rolled back at teardown — the DB state is fully isolated
per test.

### End-to-end (Playwright)
E2E tests are **opt-in** — they require real Meilisearch + Postgres
containers, a uvicorn subprocess, and a Playwright browser. Install the
browser once:
```bash
uv run playwright install chromium
```
Then run:
```bash
uv run pytest -m e2e
```

**Profile slow phases** (setup vs call vs teardown per test):

```bash
uv run pytest -m e2e --durations=30
```

**Parallel workers** (`pytest-xdist` — each worker spins up its own Postgres,
Meilisearch, and uvicorn, so avoid `-n` higher than your machine can sustain):

```bash
uv run pytest -m e2e -n auto
```

On typical laptops, `-n 2` or `-n 4` often beats `auto` when Docker is CPU-bound.

To run everything in one go:
```bash
uv run pytest -m ""  # empty marker expression, selects all
```

## Layer conventions

### Unit
Pure-python tests for small helpers (`model_utils`, `search` parsers, etc.).
No DB, no network, no file I/O beyond tempfiles.

### Integration
All integration tests use the shared `tests/conftest.py`, which provides:

- A session-scoped Postgres 17 testcontainer + Alembic-migrated schema.
- Per-test transaction isolation via a single connection + savepoint.
- Function-scoped `TestClient`s:
  - `client` — unauthenticated
  - `anon_client` — independent unauthenticated client (use when you mix
    anonymous and authenticated scenarios in one test; `client`'s cookies
    are mutated by `admin_client`/`auth_client`/`editor_client`)
  - `auth_client` — logged in as `test_user`
  - `admin_client` — logged in as `admin_user`
  - `editor_client` — logged in as a non-admin editor
  - `other_editor_client` — a second editor, for cross-ownership checks
- `db_session` — raw SQLAlchemy session for arbitrary setup/assertions.
- `_reset_audit_context` (autouse) — clears audit `ContextVar`s between tests.
- `patch_meilisearch` (autouse) — mocks every `*_INDEX` referenced by the
  app so tests never hit a real Meilisearch server.
- `png_upload` — a tuple suitable for `TestClient` image uploads.

All factories in `tests/factories/` bind to the current test's session
automatically (`bind_factories`). Factories that back
`PendingMixin` entities accept `approved=True|False` and `created_by=user`
kwargs.

### End-to-end
Lives in `tests/e2e/` and is automatically tagged with the `e2e` marker via
`pytest_collection_modifyitems`. The session-scoped `live_server` fixture
starts a real Postgres + Meilisearch pair via testcontainers, runs Alembic,
then launches uvicorn in a subprocess. Seeded user fixtures
(`e2e_admin_session`, `e2e_editor_session`, and the corresponding Playwright
`admin_browser_context` / `editor_browser_context`) sign up a fresh account
over HTTP and promote it to admin/editor with direct SQL.

Six e2e files cover different concerns. **Per-test isolation** is provided
by `_truncate_e2e_state` (autouse in `tests/e2e/conftest.py`), which
truncates every entity table after each test while preserving the
`users`/`user_sessions` rows that back the pre-authenticated browser
contexts. **HTTP setup helpers** (`make_shop`, `make_artist`, `make_tag`)
let tests provision approved/pending entities without driving the UI;
**page objects** (`tests/e2e/_pages.py`) wrap the noisier selectors so
test bodies focus on behaviour. The session-scoped `db_handle` fixture
returns a small `(sql, params) -> rows` helper backed by psycopg.

Available browser-context fixtures:
 - `admin_browser_context` — logged-in admin
 - `editor_browser_context` — logged-in non-admin editor
 - `second_editor_browser_context` — a second editor for cross-ownership /
   concurrency tests
 - `regular_user_browser_context` — logged-in user with no roles
 - `anon_browser_context` — fresh, unauthenticated context

`tests/e2e/test_flows.py` — five representative end-to-end flows:
 1. signup + login + logout round-trip
 2. admin-side shop creation
 3. editor's pending-edit approved by an admin
 4. regular user's collection add/remove
 5. pending-cascade smoke test on approval

`tests/e2e/test_ui_content.py` — content & behaviour assertions for what
the user actually sees in the browser:
 - role-gated navbar visibility (anon vs editor vs admin)
 - login / signup error messaging
 - 404 rendering for missing images and edit routes
 - pending-approval queue: visible heading, table rows, submitter
   metadata, action buttons
 - pending-edit banner appears on canonical entity views for
   editors/admins and is hidden from anonymous viewers
 - reject-edits flow removes the row from the queue and leaves
   canonical untouched
 - HTMX-driven theme switcher updates `<html>` className and persists
   across reload
 - 401/403 enforcement at the browser level for protected routes
 - top-level page titles (`<title>` element)

`tests/e2e/test_pending_chain.py` — multi-step pending-edit chain flows
across two editor browser contexts plus admin: chain build-up, in-order
collapse on `approve-edits`, reject keeps chain reachable but invisible,
delete wipes the chain hard, banner-link navigation to the pending view.

`tests/e2e/test_visibility_matrix.py` — cross-role visibility for
approved / pending / rejected entities, asserting list-page visibility
and detail-page status codes for anon / regular user / editor / admin.

`tests/e2e/test_pin_creation.py` — pin creation via HTTP (the form is
heavily Alpine-driven) covering image upload + thumbnail round-trip,
cascade-on-approval (pending shop + artist), missing-image 404, and
browser-level smoke checks on the create-pin page.

`tests/e2e/test_concurrent.py` — interleaved edits across two browser
contexts: simultaneous independent edits both land on the chain;
admin's direct canonical edit during a pending chain doesn't conflict;
approve-edits after an unrelated admin change doesn't clobber it; the
pending-edit banner disappears once the chain is approved.

The flow + UI-content tests verify routing, HTMX hydration, and the
visible surface. The chain / visibility / cascade / concurrent tests
exercise the cross-component state machines (pending → approved → public
visibility, multi-actor edit chains, cascading approval transactions)
end-to-end through the real DB and uvicorn server. Deep
business-logic coverage of single units lives in the integration layer.

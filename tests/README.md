# PinDB test suite

The suite is organised into three layers that trade fidelity for speed:

| Layer | Directory | Marker | External deps | Typical run time |
|---|---|---|---|---|
| Unit | `tests/unit/` | `unit` | none | ~8 s |
| Integration | `tests/integration/` | `integration` | Postgres (shared container) | ~35 s |
| End-to-end | `tests/e2e/` | `e2e` | Postgres + Meilisearch (shared containers), Playwright browser, real uvicorn | ~40 s |

By default `pyproject.toml` sets `-m "not e2e"`, so `uv run pytest` runs only unit + integration.

## Parallelism & containers (how the suite is fast)

Every run is **parallel by default** — the rootdir `conftest.py` sets `-n min(8, cores)`
with `dist=load` unless you pass `-n` yourself. `-n 0` and `-p no:xdist` still work.

One Postgres container serves the whole run. The xdist **controller** starts it,
migrates a *template* database once (`pindb_tmpl_<alembic head>`), and each worker
clones it with `CREATE DATABASE ... TEMPLATE` (~200 ms file copy — no per-worker
alembic). E2E runs additionally get one shared Meilisearch server; workers isolate
by index name (`pins_e2e_<worker>`).

Local knobs (CI sets neither and gets throwaway containers):

- `PINDB_TEST_KEEP_PG=1` — reattach to long-lived `pindb-test-pg` / `pindb-test-meili`
  containers, creating them on first use. Reruns skip container startup *and* the
  migration chain (the template is keyed on the alembic head). Remove with
  `docker rm -f pindb-test-pg pindb-test-meili`.
- `PINDB_TEST_PG_URL` — point at an existing Postgres (e.g. `docker-compose.dev.yaml`);
  nothing is started or stopped. `PINDB_TEST_MEILI_URL` is the e2e equivalent.

**Fork-bomb guard (do not remove):** xdist workers also fire `pytest_cmdline_main`
after resetting `numprocesses` to `None`; without the `workerinput` guard in the
rootdir `conftest.py`, every worker would become a controller and spawn 8 more
workers, exponentially (this really happened — ~1,500 processes).

### Integration file naming (convention for new tests)

Prefer **URL-mirror names** — `test_routes_<segment>.py` aligned with the route tree (for example `test_routes_pin.py`, `test_routes_misc.py`). Older modules may still use domain-style names (`test_admin_routes.py`, `test_pending_approval.py`); rename only when you are already touching a file.

Shared route-test helpers live under `tests/integration/helpers/` (`authz.py`, `pending.py`, `pin_payloads.py`). Cross-layer binaries (e.g. minimal PNG bytes) live under `tests/helpers/`.

## Running the layers

### Unit only
```bash
uv run pytest tests/unit/ -q
```

### Integration (default set + unit)
```bash
uv run pytest
```
Requires Docker (for the shared Postgres container). Each test runs inside a
transaction that is rolled back at teardown — the DB state is fully isolated
per test.

User fixtures hash constant passwords through `tests/helpers/passwords.py`
(`lru_cache`d argon2) — one real hash per password per worker instead of per
test. Tests exercising hashing itself keep calling `pindb.auth.hash_password`.

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

Parallel is the default (shared Postgres + Meilisearch; per-worker uvicorn and
browser). Pass `-n 0` to debug single-process.

To run everything in one go:
```bash
uv run pytest -m ""  # empty marker expression, selects all
```

## Layer conventions

### Unit
Pure-python tests for small helpers (`model_utils`, `search` parsers, etc.).
No DB, no network, no file I/O beyond tempfiles.

### Integration
All integration tests use the shared `tests/conftest.py`, which registers fixture plugins under `tests/fixtures/` (`database`, `search`, `app_lifecycle`, `clients`, `users`, `images`, `autouse`) after bootstrap imports in `tests/fixtures/core.py`. Together they provide:

- A per-worker database cloned from the run-wide migrated template
  (see “Parallelism & containers” above).
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
clones this worker's database from the shared template, points at the shared
Meilisearch server with a per-worker index, then launches uvicorn in a
subprocess. Seeded user fixtures
(`e2e_admin_session`, `e2e_editor_session`, and the corresponding Playwright
`admin_browser_context` / `editor_browser_context`) sign up a fresh account
over HTTP and promote it to admin/editor with direct SQL.

Specs are grouped under **`tests/e2e/<area>/test_*.py`** (flat `test_*.py` at
the e2e root is avoided). **Per-test isolation** is `_truncate_e2e_state`
(autouse in `tests/e2e/fixtures/db_isolation.py`). **`live_server`** and
containers live in `tests/e2e/fixtures/live_server.py`. Playwright/session
fixtures remain in `tests/e2e/conftest.py`.

**HTTP setup helpers** (`make_shop`, `make_artist`, `make_tag`, `make_pin`),
**page objects** (`tests/e2e/_pages.py`), and **`db_handle`** behave as before.

| Package | Purpose |
|---------|---------|
| `tests/e2e/flows/` | Short cross-cutting flows (auth session, admin shop create, pending-edit approve, collection POST, pending shop approve smoke) |
| `tests/e2e/ui/` | Navbar, auth errors, 404s, pending queue/edit Playwright checks, theme switcher, guards + `<title>` (httpx uses `ui/http.py`) |
| `tests/e2e/pins/` | Image round-trip, cascade approval + queue hints, create-pin page smoke, full-field HTTP create, client-side form validation (`pins/_helpers.py`) |
| `tests/e2e/entities/` | Shop/artist/tag create forms |
| `tests/e2e/pending/` | Edit chains, visibility matrix, concurrent edits |
| `tests/e2e/tags/` | Bulk tag creation UI |
| `tests/e2e/auth/` | OAuth + password policy flows |

Available browser-context fixtures:
 - `admin_browser_context` — logged-in admin
 - `editor_browser_context` — logged-in non-admin editor
 - `second_editor_browser_context` — a second editor for cross-ownership /
   concurrency tests
 - `regular_user_browser_context` — logged-in user with no roles
 - `anon_browser_context` — fresh, unauthenticated context

Flow and UI modules verify routing, HTMX hydration, and visible surface.
Pending / visibility / cascade / concurrent specs exercise cross-component
state machines end-to-end through the real DB and uvicorn. Deep business-logic
for single units stays in the integration layer.

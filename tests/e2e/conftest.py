"""End-to-end (Playwright) test fixtures.

Session-scoped fixtures spin up:
  * a Postgres 17 container
  * a Meilisearch container (mounted as a real search backend)
  * a uvicorn subprocess serving the real FastAPI app against those containers

Session-scoped Playwright contexts (admin/editor/second editor/regular) sign up
once per run and reuse the same logged-in browser context across tests; table
truncation between tests preserves users and sessions. Anonymous contexts stay
function-scoped to avoid cookie bleed.

E2E tests are opt-in: they're skipped by default (`addopts = -m "not e2e"`),
run them with `uv run pytest -m e2e`.

Session-scoped fixtures (``live_server``, containers, Playwright contexts) are
safe with pytest-xdist: each worker process has its own session, so workers do
not share ports, databases, or browsers.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Generator, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

_REPO_ROOT = Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# Mark every test in this package with `e2e` automatically.
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(config, items):
    e2e_root = Path(__file__).parent.resolve()
    for item in items:
        try:
            path = Path(str(item.fspath)).resolve()
        except Exception:
            continue
        try:
            path.relative_to(e2e_root)
        except ValueError:
            continue
        item.add_marker(pytest.mark.e2e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_http(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code < 500:
                return
        except Exception as err:
            last_err = err
        time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {url}: {last_err!r}")


# ---------------------------------------------------------------------------
# Session-scoped containers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Fast-fail Playwright defaults
# ---------------------------------------------------------------------------
#
# Playwright's default timeouts are 30s (actions) and 5s (expect). When an
# e2e test has a real bug the locators sit and burn that full window, turning
# a quick failure into a 30s stall *per failing assertion*. We cap both at
# something snappy so the suite fails fast. Individual tests that genuinely
# need longer can override via `page.set_default_timeout(...)` / `expect`
# `timeout=...` kwargs.
_DEFAULT_ACTION_TIMEOUT_MS = 5_000
_DEFAULT_EXPECT_TIMEOUT_MS = 5_000


def _configure_context_timeouts(context) -> None:
    """Apply the fast-fail action/navigation timeouts to a context."""
    context.set_default_timeout(_DEFAULT_ACTION_TIMEOUT_MS)
    context.set_default_navigation_timeout(_DEFAULT_ACTION_TIMEOUT_MS)


@pytest.fixture(autouse=True)
def _fast_playwright_defaults() -> None:
    """Lower Playwright default timeouts for every e2e test."""
    from playwright.sync_api import expect as _expect

    _expect.set_options(timeout=_DEFAULT_EXPECT_TIMEOUT_MS)


@pytest.fixture(autouse=True)
def _close_pages_opened_during_test(browser) -> Iterator[None]:
    """Close any pages opened during a test so session-scoped contexts don't leak.

    Session-scoped browser contexts (admin/editor/etc.) are shared across many
    tests; tests call ``context.new_page()`` freely but almost never
    ``page.close()``. Over a full session this accumulates dozens of open
    chromium pages, which degrades both the browser (slow navigations) and the
    live uvicorn server (long-idle HTMX connections). The cumulative slowdown
    was the root cause of the ``test_pending_chain`` / ``test_pending_cascade``
    failures that pushed those tests out of CI.

    This autouse fixture snapshots each context's ``pages`` list before the
    test runs and closes any pages added during the test afterwards.
    """
    snapshots: dict[int, set[int]] = {
        id(ctx): {id(page) for page in ctx.pages} for ctx in browser.contexts
    }
    yield
    for ctx in browser.contexts:
        before = snapshots.get(id(ctx), set())
        for page in list(ctx.pages):
            if id(page) not in before:
                try:
                    page.close()
                except Exception:
                    pass


@pytest.fixture(scope="session", autouse=True)
def _patch_browser_new_context(browser):
    """Wrap ``browser.new_context`` so every context gets fast-fail timeouts.

    Tests create ad-hoc contexts directly from the ``browser`` fixture; without
    this wrapper they'd fall back to the 30s Playwright default and any real
    failure would stall the suite.
    """
    original = browser.new_context

    def wrapped(*args, **kwargs):
        context = original(*args, **kwargs)
        _configure_context_timeouts(context)
        return context

    browser.new_context = wrapped  # type: ignore[method-assign]
    try:
        yield
    finally:
        browser.new_context = original  # type: ignore[method-assign]


@pytest.fixture(scope="session")
def e2e_pg_container():
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:17-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def e2e_meili_container():
    from datetime import timedelta

    from testcontainers.core.container import DockerContainer
    from testcontainers.core.wait_strategies import LogMessageWaitStrategy

    container = (
        DockerContainer("getmeili/meilisearch:v1.11")
        .with_env("MEILI_MASTER_KEY", "e2e-meili-key")
        .with_env("MEILI_ENV", "development")
        .with_exposed_ports(7700)
        .waiting_for(
            LogMessageWaitStrategy("Server listening").with_startup_timeout(
                timedelta(seconds=30)
            )
        )
    )
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def e2e_image_dir() -> Generator[Path, None, None]:
    path = Path(tempfile.mkdtemp(prefix="pindb_e2e_images_"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------------------
# Session-scoped uvicorn subprocess
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def live_server(
    e2e_pg_container, e2e_meili_container, e2e_image_dir
) -> Generator[str, None, None]:
    """Launch the app in a uvicorn subprocess and yield its base URL."""
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    pg_url = e2e_pg_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+psycopg://"
    )
    meili_host = e2e_meili_container.get_container_host_ip()
    meili_port = e2e_meili_container.get_exposed_port(7700)
    meili_url = f"http://{meili_host}:{meili_port}"

    env = {
        **os.environ,
        "DATABASE_CONNECTION": pg_url,
        "MEILISEARCH_KEY": "e2e-meili-key",
        "MEILISEARCH_URL": meili_url,
        "MEILISEARCH_INDEX": "pins_e2e",
        "SECRET_KEY": "e2e-secret-key-for-playwright-tests-only",
        "IMAGE_DIRECTORY": str(e2e_image_dir),
        "IMAGE_BACKEND": "filesystem",
        "BASE_URL": base_url,
        "SEARCH_SYNC_INTERVAL_MINUTES": "60",
        "ALLOW_TEST_OAUTH_PROVIDER": "true",
        # Explicit — pytest-env propagation through the subprocess env is
        # unreliable (CI env differed from local). The e2e suite talks to
        # uvicorn over http://127.0.0.1, so Secure session cookies are dropped
        # by httpx + Playwright and every authed request returns 401.
        "SESSION_COOKIE_SECURE": "false",
        "CSRF_ENFORCE_ORIGIN": "false",
        "CONTACT_EMAIL": "e2e@example.test",
        # Disable per-IP rate limits: all e2e traffic shares 127.0.0.1 so the
        # signup (10/hour) and login (10/minute) windows close almost
        # immediately, cascading into bogus 401s on downstream requests.
        "RATE_LIMIT_ENABLED": "false",
    }
    show_server_logs = os.environ.get("E2E_SHOW_SERVER_LOGS", "0") == "1"
    uvicorn_log_level = os.environ.get("E2E_UVICORN_LOG_LEVEL", "warning")

    # Fixtures and helpers use os.environ["DATABASE_CONNECTION"] for direct
    # psycopg access; pytest-env still has the integration placeholder unless
    # we mirror the container URL into the test process.
    prev_db = os.environ.get("DATABASE_CONNECTION")
    os.environ["DATABASE_CONNECTION"] = pg_url
    try:
        # Run migrations synchronously first, so the app starts against a ready DB.
        subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            env=env,
            check=True,
            cwd=str(_REPO_ROOT),
        )

        # Discard, don't capture — a PIPE that nobody drains fills its
        # ~64KB buffer and then blocks uvicorn on every log write, which
        # shows up downstream as random httpx.ReadTimeout /
        # expect_navigation timeouts in long test runs.
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "pindb:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                uvicorn_log_level,
            ],
            env=env,
            cwd=str(_REPO_ROOT),
            stdout=None if show_server_logs else subprocess.DEVNULL,
            stderr=None if show_server_logs else subprocess.DEVNULL,
        )
        try:
            _wait_for_http(f"{base_url}/", timeout=60)
            yield base_url
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    finally:
        if prev_db is None:
            os.environ.pop("DATABASE_CONNECTION", None)
        else:
            os.environ["DATABASE_CONNECTION"] = prev_db


# ---------------------------------------------------------------------------
# Per-test user seeding via the live HTTP API
# ---------------------------------------------------------------------------


# Strong placeholder passwords that satisfy the policy (>=12 chars, 3+ classes,
# non-obvious). Used across all e2e fixtures.
_E2E_ADMIN_PASSWORD = "E2e-Admin-Secret-9!"
_E2E_EDITOR_PASSWORD = "E2e-Editor-Secret-9!"
_E2E_EDITOR_PASSWORD_2 = "E2e-Editor-Secret-2-9!"
_E2E_REGULAR_PASSWORD = "E2e-Regular-Secret-9!"


def _signup(base_url: str, username: str, password: str) -> httpx.Client:
    client = httpx.Client(base_url=base_url, follow_redirects=False)
    signup = client.post(
        "/auth/signup",
        data={
            "username": username,
            "password": password,
            "email": f"{username}@x.test",
        },
    )
    # 303 = first-time success, 200/400 = re-signup rejected (username taken);
    # anything else (401 CSRF break, 500 server error) would silently produce a
    # logged-out client that later fails with confusing 401s.
    assert signup.status_code in (200, 303, 400), (
        f"signup of {username!r} returned {signup.status_code}: {signup.text[:300]!r}"
    )
    # Login in case signup didn't set the cookie (re-signup path).
    login = client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    assert login.status_code in (200, 303), (
        f"login of {username!r} returned {login.status_code}: {login.text[:300]!r}"
    )
    return client


@pytest.fixture
def e2e_admin_session(live_server):
    """Create (or reuse) an admin user and return a logged-in httpx.Client.

    Admin is granted directly via SQL — the running app's lifespan only
    bootstraps hardcoded usernames, not arbitrary ones.
    """
    import psycopg

    username = "e2e_admin"
    password = _E2E_ADMIN_PASSWORD
    client = _signup(live_server, username, password)

    # Promote to admin+editor directly in the DB.
    pg_url = os.environ.get("DATABASE_CONNECTION", "")
    with psycopg.connect(pg_url.replace("+psycopg", "")) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_admin = TRUE, is_editor = TRUE WHERE username = %s",
                (username,),
            )
            conn.commit()

    return client


@pytest.fixture
def e2e_editor_session(live_server):
    """Create an editor user (non-admin) and return a logged-in httpx.Client."""
    import psycopg

    username = "e2e_editor"
    password = _E2E_EDITOR_PASSWORD
    client = _signup(live_server, username, password)

    pg_url = os.environ.get("DATABASE_CONNECTION", "")
    with psycopg.connect(pg_url.replace("+psycopg", "")) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_editor = TRUE WHERE username = %s",
                (username,),
            )
            conn.commit()

    return client


# ---------------------------------------------------------------------------
# Playwright context fixtures wiring a session cookie from the httpx client
# ---------------------------------------------------------------------------


def _login_browser(browser_context, base_url: str, username: str, password: str):
    page = browser_context.new_page()
    page.goto(f"{base_url}/auth/login", wait_until="load")
    page.fill("input[name='username']", username)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    # "load" is enough for SSR + redirect; "networkidle" waits on idle network
    # and is much slower without improving assertions (expect() auto-waits).
    page.wait_for_load_state("load")
    page.close()


@pytest.fixture(scope="session")
def admin_browser_context(browser, live_server):
    """Playwright context pre-logged-in as an admin."""
    import psycopg

    username = "e2e_admin_pw"
    password = _E2E_ADMIN_PASSWORD

    with httpx.Client(base_url=live_server, follow_redirects=False) as client:
        client.post(
            "/auth/signup",
            data={
                "username": username,
                "password": password,
                "email": f"{username}@x.test",
            },
        )

    pg_url = os.environ.get("DATABASE_CONNECTION", "")
    with psycopg.connect(pg_url.replace("+psycopg", "")) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_admin = TRUE, is_editor = TRUE WHERE username = %s",
                (username,),
            )
            conn.commit()

    context = browser.new_context(base_url=live_server)
    _configure_context_timeouts(context)
    _login_browser(context, live_server, username, password)
    try:
        yield context
    finally:
        context.close()


@pytest.fixture(scope="session")
def editor_browser_context(browser, live_server):
    """Playwright context pre-logged-in as a non-admin editor."""
    import psycopg

    username = "e2e_editor_pw"
    password = _E2E_EDITOR_PASSWORD

    with httpx.Client(base_url=live_server, follow_redirects=False) as client:
        client.post(
            "/auth/signup",
            data={
                "username": username,
                "password": password,
                "email": f"{username}@x.test",
            },
        )

    pg_url = os.environ.get("DATABASE_CONNECTION", "")
    with psycopg.connect(pg_url.replace("+psycopg", "")) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_editor = TRUE WHERE username = %s",
                (username,),
            )
            conn.commit()

    context = browser.new_context(base_url=live_server)
    _configure_context_timeouts(context)
    _login_browser(context, live_server, username, password)
    try:
        yield context
    finally:
        context.close()


# ---------------------------------------------------------------------------
# Direct DB helpers + per-test truncation
# ---------------------------------------------------------------------------

# Tables to truncate between tests, in dependency order. We deliberately
# preserve `users`, `user_sessions`, and `user_auth_providers` so the
# session-scoped admin/editor users (and their cookies) survive across tests;
# everything else is per-test state.
_TRUNCATE_TABLES: tuple[str, ...] = (
    "change_log",
    "pending_edits",
    "user_favorite_pin_sets",
    "user_favorite_pins",
    "user_owned_pins",
    "user_wanted_pins",
    "pin_set_memberships",
    "pins_grades",
    "pins_links",
    "pins_tags",
    "pins_artists",
    "pins_shops",
    "pin_sets_links",
    "artists_links",
    "shops_links",
    "tag_implications",
    "tag_aliases",
    "shop_aliases",
    "artist_aliases",
    "links",
    "grades",
    "pins",
    "pin_sets",
    "tags",
    "artists",
    "shops",
)


def _pg_dsn() -> str:
    pg_url = os.environ.get("DATABASE_CONNECTION", "")
    return pg_url.replace("+psycopg", "")


@pytest.fixture(scope="session")
def _e2e_pg_conn(live_server):
    """One shared psycopg connection per xdist worker.

    `db_handle` and `_truncate_e2e_state` previously opened a fresh connection
    on every test. With ~50 tests × N workers the handshake churn was about
    20-50 ms per test. Sharing one connection (each test owns a distinct
    cursor; autocommit is handled per call) removes that overhead.
    """
    import psycopg

    conn = psycopg.connect(_pg_dsn())
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def db_handle(_e2e_pg_conn) -> Callable[..., list[tuple]]:
    """Tiny SQL execute helper.

    Returns a callable: `db_handle(sql, params=())` → list of result tuples.
    """
    import psycopg

    def _exec(sql: str, params: tuple[object, ...] = ()) -> list[tuple]:
        with _e2e_pg_conn.cursor() as cur:
            cur.execute(sql, params)
            try:
                rows = cur.fetchall()
            except psycopg.ProgrammingError:
                rows = []
        _e2e_pg_conn.commit()
        return rows

    return _exec


@pytest.fixture(autouse=True)
def _truncate_e2e_state(_e2e_pg_conn) -> Iterator[None]:
    """Wipe entity rows after each e2e test for true isolation.

    Users + sessions are preserved so pre-authenticated browser contexts
    and httpx clients keep working across tests.
    """
    yield

    from psycopg import sql as pgsql

    with _e2e_pg_conn.cursor() as cur:
        cur.execute(
            pgsql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
                pgsql.SQL(", ").join(pgsql.Identifier(t) for t in _TRUNCATE_TABLES)
            )
        )
    _e2e_pg_conn.commit()


# ---------------------------------------------------------------------------
# HTTP-driven setup helpers (much faster than driving the UI)
# ---------------------------------------------------------------------------


def _ensure_http_user(
    live_server: str, username: str, password: str, *, admin: bool, editor: bool
) -> None:
    """Idempotently sign up and promote a helper user via HTTP + direct SQL.

    Used so HTTP setup helpers (``make_shop`` / ``make_artist`` / ``make_tag``)
    work even in tests that don't request the matching
    ``admin_browser_context`` / ``editor_browser_context`` fixture.
    """
    import psycopg

    with httpx.Client(base_url=live_server, follow_redirects=False) as client:
        signup = client.post(
            "/auth/signup",
            data={
                "username": username,
                "password": password,
                "email": f"{username}@x.test",
            },
        )
        assert signup.status_code in (200, 303, 400), (
            f"signup of {username!r} returned {signup.status_code}: "
            f"{signup.text[:300]!r}"
        )

    pg_url = os.environ.get("DATABASE_CONNECTION", "")
    with psycopg.connect(pg_url.replace("+psycopg", "")) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_admin = %s, is_editor = %s WHERE username = %s",
                (admin, admin or editor, username),
            )
            conn.commit()


@pytest.fixture(scope="session")
def _http_setup_users(live_server):
    """Session-scoped seed of the admin/editor users used by HTTP helpers."""
    _ensure_http_user(
        live_server, "e2e_admin_pw", _E2E_ADMIN_PASSWORD, admin=True, editor=True
    )
    _ensure_http_user(
        live_server, "e2e_editor_pw", _E2E_EDITOR_PASSWORD, admin=False, editor=True
    )


@pytest.fixture(scope="session")
def admin_http_client(
    live_server, _http_setup_users
) -> Generator[httpx.Client, None, None]:
    """One logged-in admin httpx client per worker (avoids burning /auth/login rate limits)."""
    client = httpx.Client(base_url=live_server, follow_redirects=False)
    login = client.post(
        "/auth/login",
        data={"username": "e2e_admin_pw", "password": _E2E_ADMIN_PASSWORD},
    )
    assert login.status_code == 303, (
        f"e2e admin HTTP login failed: {login.status_code} {login.text[:500]!r}"
    )
    try:
        yield client
    finally:
        client.close()


@pytest.fixture(scope="session")
def anon_http_client(live_server) -> Generator[httpx.Client, None, None]:
    """Unauthenticated httpx client bound to the live server.

    Used by the httpx-based ``test_ui_content`` assertions (navbar
    visibility, page titles, auth guards) that only need the rendered HTML
    and don't exercise client-side scripts.
    """
    with httpx.Client(base_url=live_server, follow_redirects=False) as client:
        yield client


@pytest.fixture(scope="session")
def editor_http_client(
    live_server, _http_setup_users
) -> Generator[httpx.Client, None, None]:
    """One logged-in editor httpx client per worker."""
    client = httpx.Client(base_url=live_server, follow_redirects=False)
    login = client.post(
        "/auth/login",
        data={"username": "e2e_editor_pw", "password": _E2E_EDITOR_PASSWORD},
    )
    assert login.status_code == 303, (
        f"e2e editor HTTP login failed: {login.status_code} {login.text[:500]!r}"
    )
    try:
        yield client
    finally:
        client.close()


def _create_entity_http(
    admin_client: httpx.Client,
    editor_client: httpx.Client,
    db_handle: Callable[..., list[tuple]],
    *,
    endpoint: str,
    table: str,
    name: str,
    extra_form: dict[str, str] | None = None,
    approved: bool,
) -> dict[str, Any]:
    http = admin_client if approved else editor_client
    data = {"name": name, **(extra_form or {})}
    response = http.post(endpoint, data=data, headers={"HX-Request": "true"})
    assert response.status_code == 200, (
        f"{endpoint} failed: {response.status_code} {response.text[:300]}"
    )

    rows = db_handle(
        f"SELECT id, name, approved_at IS NOT NULL FROM {table} WHERE name = %s",
        (name,),
    )
    assert rows, f"{table} row {name!r} not found after create"
    entity_id, entity_name, is_approved = rows[0]
    return {"id": entity_id, "name": entity_name, "approved": is_approved}


@pytest.fixture
def make_shop(
    admin_http_client, editor_http_client, db_handle
) -> Callable[..., dict[str, Any]]:
    def _make(
        name: str,
        *,
        description: str = "",
        approved: bool = True,
    ) -> dict[str, Any]:
        return _create_entity_http(
            admin_http_client,
            editor_http_client,
            db_handle,
            endpoint="/create/shop",
            table="shops",
            name=name,
            extra_form={"description": description},
            approved=approved,
        )

    return _make


@pytest.fixture
def make_artist(
    admin_http_client, editor_http_client, db_handle
) -> Callable[..., dict[str, Any]]:
    def _make(
        name: str,
        *,
        description: str = "",
        approved: bool = True,
    ) -> dict[str, Any]:
        return _create_entity_http(
            admin_http_client,
            editor_http_client,
            db_handle,
            endpoint="/create/artist",
            table="artists",
            name=name,
            extra_form={"description": description},
            approved=approved,
        )

    return _make


@pytest.fixture
def make_tag(
    admin_http_client, editor_http_client, db_handle
) -> Callable[..., dict[str, Any]]:
    def _make(name: str, *, approved: bool = True) -> dict[str, Any]:
        return _create_entity_http(
            admin_http_client,
            editor_http_client,
            db_handle,
            endpoint="/create/tag",
            table="tags",
            name=name,
            extra_form={"category": "general"},
            approved=approved,
        )

    return _make


def _tiny_png() -> bytes:
    """Smallest valid PNG Pillow will open (1x1 black pixel).

    Inlined here so ``make_pin`` doesn't cross the
    ``tests/e2e/test_pin_creation.py`` import boundary.
    """
    import struct
    import zlib

    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(typ: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + typ
            + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\x00\x00\x00")
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture
def make_pin(
    admin_http_client, editor_http_client, db_handle, make_shop
) -> Callable[..., dict[str, Any]]:
    """Create an approved pin via HTTP with a real (1x1) PNG attached."""
    import io

    def _make(
        name: str = "SeedPin",
        *,
        shop_name: str | None = None,
        approved: bool = True,
    ) -> dict[str, Any]:
        http = admin_http_client if approved else editor_http_client
        shop = make_shop(shop_name or f"{name}Shop", approved=True)

        files = {
            "front_image": ("front.png", io.BytesIO(_tiny_png()), "image/png"),
        }
        data: dict[str, str | list[str]] = {
            "name": name,
            "acquisition_type": "single",
            "grade_names": "standard",
            "grade_prices": "",
            # 999 = "Unknown" currency sentinel seeded in alembic migration
            # d1e2f3a4b5c6_unknown_defaults.
            "currency_id": "999",
            "posts": "1",
            "shop_ids": [str(shop["id"])],
        }
        response = http.post("/create/pin", data=data, files=files)
        assert response.status_code == 200, (
            f"/create/pin failed: {response.status_code} {response.text[:300]}"
        )

        rows = db_handle(
            "SELECT id, name, approved_at IS NOT NULL FROM pins WHERE name = %s",
            (name,),
        )
        assert rows, f"pin {name!r} not found after create"
        pin_id, pin_name, is_approved = rows[0]
        return {"id": pin_id, "name": pin_name, "approved": is_approved}

    return _make


@pytest.fixture(scope="session")
def second_editor_browser_context(browser, live_server) -> Iterator:
    """A second non-admin editor for cross-ownership / concurrency tests."""
    import psycopg

    username = "e2e_editor_pw_2"
    password = _E2E_EDITOR_PASSWORD_2

    with httpx.Client(base_url=live_server, follow_redirects=False) as client:
        client.post(
            "/auth/signup",
            data={
                "username": username,
                "password": password,
                "email": f"{username}@x.test",
            },
        )

    pg_url = os.environ.get("DATABASE_CONNECTION", "")
    with psycopg.connect(pg_url.replace("+psycopg", "")) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_editor = TRUE WHERE username = %s",
                (username,),
            )
            conn.commit()

    context = browser.new_context(base_url=live_server)
    _configure_context_timeouts(context)
    _login_browser(context, live_server, username, password)
    try:
        yield context
    finally:
        context.close()


@pytest.fixture(scope="session")
def regular_user_browser_context(browser, live_server) -> Iterator:
    """A logged-in user with no admin/editor roles."""
    import psycopg

    username = "e2e_regular"
    password = _E2E_REGULAR_PASSWORD

    with httpx.Client(base_url=live_server, follow_redirects=False) as client:
        client.post(
            "/auth/signup",
            data={
                "username": username,
                "password": password,
                "email": f"{username}@x.test",
            },
        )

    pg_url = os.environ.get("DATABASE_CONNECTION", "")
    with psycopg.connect(pg_url.replace("+psycopg", "")) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_admin = FALSE, is_editor = FALSE WHERE username = %s",
                (username,),
            )
            conn.commit()

    context = browser.new_context(base_url=live_server)
    _configure_context_timeouts(context)
    _login_browser(context, live_server, username, password)
    try:
        yield context
    finally:
        context.close()


@pytest.fixture
def anon_browser_context(browser, live_server) -> Iterator:
    """A clean browser context with no session cookie."""
    context = browser.new_context(base_url=live_server)
    _configure_context_timeouts(context)
    try:
        yield context
    finally:
        context.close()


@pytest.fixture
def register_test_oauth_identity(live_server) -> Callable[..., str]:
    """Register a canned OAuth identity with the in-app test provider.

    Returns a function ``(identity_id, provider, **fields) -> identity_id``
    that POSTs to ``/auth/_test-oauth/register`` so subsequent
    ``/auth/_test-oauth/start`` calls return the requested identity.
    """

    def _register(
        identity_id: str,
        *,
        provider: str = "google",
        provider_user_id: str | None = None,
        email: str | None = None,
        email_verified: bool = True,
        username_hint: str = "e2e_oauth",
        provider_username: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "identity_id": identity_id,
            "provider": provider,
            "provider_user_id": provider_user_id or identity_id,
            "email": email,
            "email_verified": email_verified,
            "username_hint": username_hint,
            "provider_username": provider_username,
        }
        resp = httpx.post(f"{live_server}/auth/_test-oauth/register", json=payload)
        resp.raise_for_status()
        return identity_id

    return _register

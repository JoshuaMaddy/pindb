"""End-to-end (Playwright) test fixtures.

Session-scoped fixtures spin up:
  * a Postgres 17 container
  * a Meilisearch container (mounted as a real search backend)
  * a uvicorn subprocess serving the real FastAPI app against those containers

Session-scoped Playwright contexts (admin/editor/second editor/regular) are
authenticated from the session tokens seeded into the template database
(``tests/fixtures/e2e_users.py``) — no signup, no login — and reused across
tests; table truncation between tests preserves users and sessions. Anonymous
contexts stay function-scoped to avoid cookie bleed.

E2E tests are opt-in: they're skipped by default (`addopts = -m "not e2e"`),
run them with `uv run pytest -m e2e`.

Session-scoped fixtures (``live_server``, containers, Playwright contexts) are
safe with pytest-xdist: each worker process has its own session, so workers do
not share ports, databases, or browsers.
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.fixtures import e2e_users

# Fixture plugins (live_server, db_isolation) are registered from the top-level
# tests/conftest.py — pytest no longer allows ``pytest_plugins`` in a
# non-top-level conftest.


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

# Navigation gets a longer leash than actions. A failing *locator* is waiting on
# something that will never arrive, so 5s is the right amount of patience. A
# navigation is waiting on the page, and ~33 specs navigate with
# `wait_until="networkidle"`, which needs 500ms of *zero* network activity: the
# islands lazily `import()` their chunks and several pages fetch their select
# options on load, so the settle point sits a long way after first paint. Under
# xdist the workers share a CPU and that can overrun 5s, timing out `goto` on
# whichever spec drew the short straw — the intermittent
# "Page.goto: Timeout 5000ms exceeded" that has been blamed on flaky tests.
# This costs nothing on a healthy run; it only stops the suite from giving up
# on a page that was still loading.
_DEFAULT_NAVIGATION_TIMEOUT_MS = 20_000
_HTTP_TIMEOUT = httpx.Timeout(15.0)


def _configure_context_timeouts(context) -> None:
    """Apply the fast-fail action timeouts, with a longer navigation window."""
    context.set_default_timeout(_DEFAULT_ACTION_TIMEOUT_MS)
    context.set_default_navigation_timeout(_DEFAULT_NAVIGATION_TIMEOUT_MS)


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
    was the root cause of the ``pending/test_edit_chain.py`` slow tests /
    pending-cascade flows
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


# ---------------------------------------------------------------------------
# Authenticated fixtures
#
# The user cast and its session tokens are seeded into the template database
# every worker clones (tests/fixtures/e2e_users.py), so nothing here signs up or
# logs in — a context or client is authenticated by being handed the cookie. That
# removed six argon2 hashes and six argon2 verifies from every worker's session
# setup, which was the bulk of the suite's wall clock.
# ---------------------------------------------------------------------------


# Kept as module-level names because tests import them to drive the real login
# form (password-policy and auth flows).
_E2E_ADMIN_PASSWORD = e2e_users.ADMIN.password
_E2E_EDITOR_PASSWORD = e2e_users.EDITOR.password
_E2E_EDITOR_PASSWORD_2 = e2e_users.EDITOR_2.password
_E2E_REGULAR_PASSWORD = e2e_users.REGULAR.password


def _authed_client(base_url: str, user: e2e_users.E2EUser) -> httpx.Client:
    """An httpx client already holding *user*'s seeded session cookie."""
    return httpx.Client(
        base_url=base_url,
        follow_redirects=False,
        timeout=_HTTP_TIMEOUT,
        cookies={e2e_users.SESSION_COOKIE: user.token},
    )


def _authed_context(browser, base_url: str, user: e2e_users.E2EUser):
    """A Playwright context already holding *user*'s seeded session cookie."""
    context = browser.new_context(
        base_url=base_url, storage_state=user.storage_state(base_url)
    )
    _configure_context_timeouts(context)
    return context


@pytest.fixture
def e2e_admin_session(live_server) -> Iterator[httpx.Client]:
    """A logged-in admin httpx.Client (seeded user, seeded session)."""
    with _authed_client(live_server, e2e_users.ADMIN_HTTP) as client:
        yield client


@pytest.fixture
def e2e_editor_session(live_server) -> Iterator[httpx.Client]:
    """A logged-in non-admin editor httpx.Client (seeded user, seeded session)."""
    with _authed_client(live_server, e2e_users.EDITOR_HTTP) as client:
        yield client


# ---------------------------------------------------------------------------
# Playwright context fixtures wiring a session cookie from the httpx client
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def admin_browser_context(browser, live_server):
    """Playwright context pre-logged-in as an admin."""
    context = _authed_context(browser, live_server, e2e_users.ADMIN)
    try:
        yield context
    finally:
        context.close()


@pytest.fixture(scope="session")
def editor_browser_context(browser, live_server):
    """Playwright context pre-logged-in as a non-admin editor."""
    context = _authed_context(browser, live_server, e2e_users.EDITOR)
    try:
        yield context
    finally:
        context.close()


# ---------------------------------------------------------------------------
# HTTP-driven setup helpers (much faster than driving the UI)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def admin_http_client(live_server) -> Generator[httpx.Client, None, None]:
    """One admin httpx client per worker, holding the seeded session cookie."""
    with _authed_client(live_server, e2e_users.ADMIN) as client:
        yield client


@pytest.fixture(scope="session")
def anon_http_client(live_server) -> Generator[httpx.Client, None, None]:
    """Unauthenticated httpx client bound to the live server.

    Used by the httpx-based ``ui/test_*.py`` assertions (navbar
    visibility, page titles, auth guards) that only need the rendered HTML
    and don't exercise client-side scripts.
    """
    with httpx.Client(
        base_url=live_server, follow_redirects=False, timeout=_HTTP_TIMEOUT
    ) as client:
        yield client


@pytest.fixture(scope="session")
def editor_http_client(live_server) -> Generator[httpx.Client, None, None]:
    """One editor httpx client per worker, holding the seeded session cookie."""
    with _authed_client(live_server, e2e_users.EDITOR) as client:
        yield client


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


@pytest.fixture
def make_pin(
    admin_http_client, editor_http_client, db_handle, make_shop, make_tag
) -> Callable[..., dict[str, Any]]:
    """Create an approved pin via HTTP with a real (1x1) PNG attached."""
    import io

    from tests.helpers.binary_fixtures import tiny_png_bytes

    def _make(
        name: str = "SeedPin",
        *,
        shop_name: str | None = None,
        tag_names: list[str] | None = None,
        approved: bool = True,
    ) -> dict[str, Any]:
        http = admin_http_client if approved else editor_http_client
        shop = make_shop(shop_name or f"{name}Shop", approved=True)
        tag_ids: list[str] = [
            str(make_tag(tag_name, approved=True)["id"])
            for tag_name in (tag_names or [])
        ]

        files = {
            "front_image": ("front.png", io.BytesIO(tiny_png_bytes()), "image/png"),
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
        if tag_ids:
            data["tag_ids"] = tag_ids
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
    context = _authed_context(browser, live_server, e2e_users.EDITOR_2)
    try:
        yield context
    finally:
        context.close()


@pytest.fixture(scope="session")
def regular_user_browser_context(browser, live_server) -> Iterator:
    """A logged-in user with no admin/editor roles."""
    context = _authed_context(browser, live_server, e2e_users.REGULAR)
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


# ---------------------------------------------------------------------------
# Screenshot assertions (visual parity for island ports; see screenshots.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def assert_screenshot(request: pytest.FixtureRequest) -> Callable[..., None]:
    """``assert_screenshot(page_or_locator, name)`` bound to --update-screenshots."""
    from tests.e2e.screenshots import assert_screenshot as _assert_screenshot

    update: bool = bool(request.config.getoption("--update-screenshots"))

    def _assert(target, name: str) -> None:
        _assert_screenshot(target, name, update=update)

    return _assert

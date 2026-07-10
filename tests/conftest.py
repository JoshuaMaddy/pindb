"""
Root conftest — loads shared fixture plugins for integration tests.

IMPORTANT: pytest-env (configured in pyproject.toml) sets the required env vars
(DATABASE_CONNECTION, MEILISEARCH_KEY, SECRET_KEY, IMAGE_DIRECTORY) during pytest
startup, BEFORE this file is imported. That satisfies Configuration()'s required
fields at import time. The real test DB connection is injected later via
session_maker.configure() in patch_session_maker.

Fixture implementations live under ``tests/fixtures/``; this file only registers
plugins and triggers bootstrap imports via ``tests.fixtures.core``.
"""

from __future__ import annotations

import pytest

import tests.fixtures.core  # noqa: F401  — side-effect imports (image dir, app, Meili modules)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-screenshots",
        action="store_true",
        default=False,
        help="Regenerate e2e screenshot baselines instead of asserting against them.",
    )


pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.search",
    "tests.fixtures.app_lifecycle",
    "tests.fixtures.clients",
    "tests.fixtures.users",
    "tests.fixtures.images",
    "tests.fixtures.autouse",
    # e2e plugins must be registered from this top-level conftest (pytest no
    # longer allows ``pytest_plugins`` in a non-top-level conftest). These
    # modules only import stdlib/httpx at import time; their container and
    # Playwright work happens lazily inside fixtures requested by e2e tests, so
    # registering them globally stays cheap for unit/integration runs.
    "tests.e2e.fixtures.live_server",
    "tests.e2e.fixtures.db_isolation",
]

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

import tests.fixtures.core  # noqa: F401  — side-effect imports (image dir, app, Meili modules)

pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.search",
    "tests.fixtures.app_lifecycle",
    "tests.fixtures.clients",
    "tests.fixtures.users",
    "tests.fixtures.images",
    "tests.fixtures.autouse",
]

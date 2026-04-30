"""FastAPI app fixture with lifespan disabled for tests."""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest

from tests.fixtures import core


@pytest.fixture(scope="session")
def test_app():
    """
    Replace the app's lifespan with a no-op to prevent:
      - APScheduler starting a background thread
      - Meilisearch index setup (setup_index / update_all)
      - Currency seeding and admin bootstrap (handled by explicit fixtures)
    """

    @asynccontextmanager
    async def null_lifespan(_app):
        yield

    original_lifespan = core.app.router.lifespan_context
    core.app.router.lifespan_context = null_lifespan
    yield core.app
    core.app.router.lifespan_context = original_lifespan

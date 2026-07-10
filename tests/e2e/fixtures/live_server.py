"""Postgres + Meilisearch testcontainers and uvicorn subprocess for e2e."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


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


@pytest.fixture(scope="session")
def e2e_database_url(request: pytest.FixtureRequest) -> str:
    """
    This worker's own database, cloned from the run-wide migrated template.

    Shares the controller's single Postgres container with the integration suite,
    so e2e pays neither a container startup nor an alembic chain per worker.
    """
    from tests.fixtures import _pg
    from tests.fixtures.database import pg_target

    base_url, template = pg_target(request.config)
    return _pg.clone_template(base_url, template, _pg.worker_db_name("pindb_e2e"))


@pytest.fixture(scope="session")
def e2e_meili_url(request: pytest.FixtureRequest) -> str:
    """
    The run-wide shared Meilisearch server, provisioned by the rootdir conftest.

    Workers isolate by index name (see ``live_server``), so one server replaces
    the previous eight per-worker containers.
    """
    from tests.fixtures import _meili

    workerinput = getattr(request.config, "workerinput", {})
    url = workerinput.get("pindb_meili_url") or os.environ.get(_meili.MEILI_URL_ENV)
    if not url:
        raise RuntimeError(
            "Meilisearch was never provisioned; e2e runs must select tests with "
            "-m e2e so conftest.py::_wants_meili starts the shared server."
        )
    return url


@pytest.fixture(scope="session")
def e2e_image_dir() -> Generator[Path, None, None]:
    path = Path(tempfile.mkdtemp(prefix="pindb_e2e_images_"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="session")
def live_server(
    e2e_database_url, e2e_meili_url, e2e_image_dir
) -> Generator[str, None, None]:
    """Launch the app in a uvicorn subprocess and yield its base URL."""
    from tests.fixtures import _meili

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    pg_url = e2e_database_url
    async_pg_url = pg_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")

    # Per-worker index on the shared server; dropped first so a kept container
    # (PINDB_TEST_KEEP_PG=1) never leaks documents from a previous run.
    meili_index = f"pins_e2e_{os.environ.get('PYTEST_XDIST_WORKER', 'main')}"
    _meili.delete_index(e2e_meili_url, meili_index)

    env = {
        **os.environ,
        "DATABASE_CONNECTION": async_pg_url,
        "DATABASE_CONNECTION_SYNC": pg_url,
        "MEILISEARCH_KEY": _meili.MEILI_MASTER_KEY,
        "MEILISEARCH_URL": e2e_meili_url,
        "MEILISEARCH_INDEX": meili_index,
        "SECRET_KEY": "e2e-secret-key-for-playwright-tests-only",
        "IMAGE_DIRECTORY": str(e2e_image_dir),
        "IMAGE_BACKEND": "filesystem",
        "BASE_URL": base_url,
        "SEARCH_SYNC_INTERVAL_MINUTES": "60",
        "ALLOW_TEST_OAUTH_PROVIDER": "true",
        "SESSION_COOKIE_SECURE": "false",
        "CSRF_ENFORCE_ORIGIN": "false",
        "CONTACT_EMAIL": "e2e@example.test",
        "RATE_LIMIT_ENABLED": "false",
    }
    show_server_logs = os.environ.get("E2E_SHOW_SERVER_LOGS", "0") == "1"
    uvicorn_log_level = os.environ.get("E2E_UVICORN_LOG_LEVEL", "warning")

    # db_isolation.py builds its psycopg DSN from DATABASE_CONNECTION.
    prev_db = os.environ.get("DATABASE_CONNECTION")
    prev_db_sync = os.environ.get("DATABASE_CONNECTION_SYNC")
    os.environ["DATABASE_CONNECTION"] = pg_url
    os.environ["DATABASE_CONNECTION_SYNC"] = pg_url
    try:
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
            cwd=str(REPO_ROOT),
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
        if prev_db_sync is None:
            os.environ.pop("DATABASE_CONNECTION_SYNC", None)
        else:
            os.environ["DATABASE_CONNECTION_SYNC"] = prev_db_sync

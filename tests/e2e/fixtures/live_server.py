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
    async_pg_url = pg_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
    meili_host = e2e_meili_container.get_container_host_ip()
    meili_port = e2e_meili_container.get_exposed_port(7700)
    meili_url = f"http://{meili_host}:{meili_port}"

    env = {
        **os.environ,
        "DATABASE_CONNECTION": async_pg_url,
        "DATABASE_CONNECTION_SYNC": pg_url,
        "MEILISEARCH_KEY": "e2e-meili-key",
        "MEILISEARCH_URL": meili_url,
        "MEILISEARCH_INDEX": "pins_e2e",
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

    prev_db = os.environ.get("DATABASE_CONNECTION")
    prev_db_sync = os.environ.get("DATABASE_CONNECTION_SYNC")
    os.environ["DATABASE_CONNECTION"] = pg_url
    os.environ["DATABASE_CONNECTION_SYNC"] = pg_url
    try:
        subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            env=env,
            check=True,
            cwd=str(REPO_ROOT),
        )

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

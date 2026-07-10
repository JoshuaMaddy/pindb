"""Shared Meilisearch container for e2e, controller-owned like ``_pg``.

Previously every xdist worker started its own Meilisearch testcontainer (plus
its own Ryuk reaper) — 8 containers per e2e run. One server is plenty: workers
isolate themselves by index name (``pins_e2e_<worker>``), which the app reads
from ``MEILISEARCH_INDEX``.

``PINDB_TEST_KEEP_PG=1`` keeps this container too (``pindb-test-meili``), so a
rerun skips the boot. Each worker deletes its own index before starting uvicorn,
so state never leaks between runs. Tear down with ``docker rm -f pindb-test-meili``.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

MEILI_IMAGE = "getmeili/meilisearch:v1.11"
MEILI_MASTER_KEY = "e2e-meili-key"

KEEP_CONTAINER_NAME = "pindb-test-meili"

# Controller → ``-n 0`` / ``-p no:xdist`` handoff, mirroring _pg's env fallback.
MEILI_URL_ENV = "_PINDB_MEILI_URL"


def wait_healthy(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{url}/health", timeout=2.0).status_code == 200:
                return
        except Exception as err:  # noqa: BLE001 - connection errors vary by OS
            last = err
        time.sleep(0.25)
    raise RuntimeError(f"Meilisearch never became healthy at {url}: {last!r}")


def start_kept_container() -> str:
    """Reattach to (or create) the long-lived ``pindb-test-meili`` container."""
    import docker
    from docker.errors import NotFound

    from tests.fixtures._pg import _host_port

    client = docker.from_env()
    try:
        container = client.containers.get(KEEP_CONTAINER_NAME)
        if container.status != "running":
            container.start()
    except NotFound:
        container = client.containers.run(
            MEILI_IMAGE,
            name=KEEP_CONTAINER_NAME,
            detach=True,
            environment={
                "MEILI_MASTER_KEY": MEILI_MASTER_KEY,
                "MEILI_ENV": "development",
            },
            ports={"7700/tcp": None},
        )

    url = f"http://127.0.0.1:{_host_port(container, port='7700/tcp')}"
    wait_healthy(url)
    return url


def start_throwaway_container() -> tuple[Any, str]:
    """One per-run Meilisearch container; caller stops it in ``pytest_unconfigure``."""
    from datetime import timedelta

    from testcontainers.core.container import DockerContainer
    from testcontainers.core.wait_strategies import LogMessageWaitStrategy

    container = (
        DockerContainer(MEILI_IMAGE)
        .with_env("MEILI_MASTER_KEY", MEILI_MASTER_KEY)
        .with_env("MEILI_ENV", "development")
        .with_exposed_ports(7700)
        .waiting_for(
            LogMessageWaitStrategy("Server listening").with_startup_timeout(
                timedelta(seconds=30)
            )
        )
    )
    container.start()
    url = (
        f"http://{container.get_container_host_ip()}:{container.get_exposed_port(7700)}"
    )
    return container, url


def delete_index(url: str, index: str) -> None:
    """Drop one worker's index so a kept server starts each run clean.

    Meilisearch queues the deletion as an async task, but the task queue is
    serialized: the app's later index creation is processed after this delete.
    """
    httpx.delete(
        f"{url}/indexes/{index}",
        headers={"Authorization": f"Bearer {MEILI_MASTER_KEY}"},
        timeout=10.0,
    )

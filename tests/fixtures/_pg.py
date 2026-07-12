"""
Postgres container lifecycle and template-database plumbing for the test suite.

One Postgres container serves the whole pytest run. It is migrated once into a
*template* database named ``pindb_tmpl_<alembic head>``; every xdist worker then
clones that template with ``CREATE DATABASE ... TEMPLATE``, which is a file copy
(~200ms) rather than a 25-revision alembic chain.

Naming the template after the alembic head means an unchanged migration chain is
detected across runs: with a kept container (``PINDB_TEST_KEEP_PG=1``) the second
run finds the template already built and skips alembic entirely.

Nothing here is a fixture — the rootdir ``conftest.py`` drives it from the xdist
controller, and ``tests/fixtures/database.py`` consumes it from the workers.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, create_engine, text
from sqlalchemy.engine import make_url

from tests.fixtures import e2e_users

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

PG_IMAGE = "postgres:17-alpine"

# Durability is worthless for a database we throw away, and TRUNCATE-per-test is
# the suite's hottest write path. max_connections is raised because every xdist
# worker holds a pooled sync engine against the one shared server.
PG_COMMAND = (
    "-c fsync=off"
    " -c full_page_writes=off"
    " -c synchronous_commit=off"
    " -c max_connections=300"
)

# Kept-container identity. Fixed credentials so a later run can reattach by name
# without knowing anything the previous run generated.
KEEP_CONTAINER_NAME = "pindb-test-pg"
KEEP_USER = "pindb_test"
KEEP_PASSWORD = "pindb_test"
KEEP_DB = "pindb_test"

# Serializes CREATE DATABASE across xdist workers *and* across concurrent pytest
# runs sharing a kept container. Postgres refuses to copy a template that has a
# live session, and two simultaneous copies of one template collide.
_LOCK_KEY = 920475001

_TEMPLATE_READY_COMMENT = "ready"

# ``currencies`` carries AuditMixin FKs to ``users``, so TRUNCATE ... CASCADE on
# users wipes it no matter how the truncate list is written. Rather than re-insert
# 170 rows from Python on every test, the template keeps a plain copy with no
# foreign keys, and teardown restores from it in one server-side statement.
CURRENCY_SEED_TABLE = "_pindb_currency_seed"

# How the controller reaches a ``-n 0`` / ``-p no:xdist`` run, which has no worker
# and therefore never sees ``workerinput``.
PG_BASE_URL_ENV = "_PINDB_PG_BASE_URL"
TEMPLATE_DB_ENV = "_PINDB_TMPL_DB"


def _ensure_image_dir() -> None:
    """``pindb.config`` validates IMAGE_DIRECTORY at import; create it first."""
    os.makedirs(
        os.environ.get("IMAGE_DIRECTORY", "/tmp/pindb_test_images"), exist_ok=True
    )


def swap_db(url: str, dbname: str) -> str:
    return make_url(url).set(database=dbname).render_as_string(hide_password=False)


def _alembic_config():
    """
    An alembic Config with no ini file behind it.

    Pointing Config at ``alembic.ini`` would make ``alembic/env.py`` call
    ``fileConfig()``, which reconfigures the root logger and disables every
    existing one — fine in the old subprocess, hostile in the pytest process.
    ``script_location`` is the only ini setting env.py needs; it overrides
    ``sqlalchemy.url`` itself.
    """
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    return config


def head_revision() -> str:
    """Current alembic head, read from the script directory (no subprocess)."""
    from alembic.script import ScriptDirectory

    head = ScriptDirectory.from_config(_alembic_config()).get_current_head()
    if head is None:
        raise RuntimeError("alembic has no head revision")
    return head


def alembic_upgrade_inprocess(sync_url: str) -> None:
    """
    Run ``alembic upgrade head`` against ``sync_url`` without spawning a process.

    ``alembic/env.py`` calls ``config.set_main_option("sqlalchemy.url",
    CONFIGURATION.database_connection_sync)`` at run time, so pre-seeding the ini
    option or the environment has no effect — the setting on ``CONFIGURATION``
    itself is the only override point.
    """
    from alembic import command

    _ensure_image_dir()
    from pindb.config import CONFIGURATION

    previous = CONFIGURATION.database_connection_sync
    CONFIGURATION.database_connection_sync = sync_url
    try:
        command.upgrade(_alembic_config(), "head")
    finally:
        CONFIGURATION.database_connection_sync = previous


def seed_currencies(sync_url: str) -> None:
    """Insert the 269 ISO currencies (including the id=999 ``Unknown`` sentinel)."""
    from csv import DictReader
    from datetime import datetime, timezone

    csv_path = REPO_ROOT / "src" / "pindb" / "database" / "data" / "currencies.csv"
    with csv_path.open(newline="") as currencies_file:
        # A core INSERT bypasses the audit before_flush that populates created_at
        # on ORM adds, and the column is NOT NULL.
        now = datetime.now(timezone.utc)
        rows = [
            {
                "id": int(row["id"]),
                "name": row["name"],
                "code": row["code"],
                "created_at": now,
            }
            for row in DictReader(currencies_file)
        ]

    engine = create_engine(sync_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO currencies (id, name, code, created_at)"
                    " VALUES (:id, :name, :code, :created_at)"
                    " ON CONFLICT (id) DO NOTHING"
                ),
                rows,
            )
            connection.exec_driver_sql(
                f"CREATE UNLOGGED TABLE {CURRENCY_SEED_TABLE} AS"
                " SELECT id, name, code, created_at FROM currencies"
            )
    finally:
        engine.dispose()


def _admin_engine(base_url: str):
    return create_engine(base_url, isolation_level="AUTOCOMMIT")


def _database_exists(connection: Connection, name: str) -> bool:
    return bool(
        connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        ).scalar()
    )


def _template_is_ready(connection: Connection, name: str) -> bool:
    comment = connection.execute(
        text(
            "SELECT shobj_description(oid, 'pg_database')"
            " FROM pg_database WHERE datname = :name"
        ),
        {"name": name},
    ).scalar()
    return comment == _TEMPLATE_READY_COMMENT


def template_name(*, seed_e2e: bool) -> str:
    """Template database name for this alembic head and seed set.

    The e2e cast lives in its own template: integration tests assert against user
    tables and would see six accounts they never created. Keying the name on both
    the head and the seed version means a checkout that changes either builds a
    fresh template instead of silently reusing a stale one.
    """
    if not seed_e2e:
        return f"pindb_tmpl_{head_revision()}"
    return f"pindb_tmpl_{head_revision()}_e2e{e2e_users.SEED_VERSION}"


def build_template(base_url: str, *, seed_e2e: bool = False) -> str:
    """
    Ensure the template database exists, is migrated, and holds the seed data.

    Returns the template database name. Idempotent: a template that already
    carries the "ready" comment is reused untouched, so a rerun against a kept
    container never runs alembic.

    Every engine opened here is disposed before returning — Postgres will not
    copy a template that has a live session.
    """
    template = template_name(seed_e2e=seed_e2e)
    admin = _admin_engine(base_url)
    try:
        with admin.connect() as connection:
            connection.execute(
                text("SELECT pg_advisory_lock(:key)"), {"key": _LOCK_KEY}
            )
            try:
                if _database_exists(connection, template):
                    if _template_is_ready(connection, template):
                        return template
                    # A previous run died mid-build; the template is unusable.
                    connection.exec_driver_sql(
                        f'DROP DATABASE "{template}" WITH (FORCE)'
                    )
                connection.exec_driver_sql(f'CREATE DATABASE "{template}"')
                _populate_template(base_url, template, seed_e2e=seed_e2e)
                connection.exec_driver_sql(
                    f"COMMENT ON DATABASE \"{template}\" IS '{_TEMPLATE_READY_COMMENT}'"
                )
                return template
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": _LOCK_KEY}
                )
    finally:
        admin.dispose()


def _populate_template(base_url: str, template: str, *, seed_e2e: bool) -> None:
    template_url = swap_db(base_url, template)
    alembic_upgrade_inprocess(template_url)
    seed_currencies(template_url)
    if seed_e2e:
        e2e_users.seed_e2e_users(template_url)


def clone_template(base_url: str, template: str, dbname: str) -> str:
    """
    Create ``dbname`` as a copy of ``template`` and return its connection URL.

    ``WITH (FORCE)`` drops a database left behind by a crashed run, including one
    that still has pooled connections attached.
    """
    admin = _admin_engine(base_url)
    try:
        with admin.connect() as connection:
            connection.execute(
                text("SELECT pg_advisory_lock(:key)"), {"key": _LOCK_KEY}
            )
            try:
                connection.exec_driver_sql(
                    f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)'
                )
                connection.exec_driver_sql(
                    f'CREATE DATABASE "{dbname}" TEMPLATE "{template}"'
                )
            finally:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": _LOCK_KEY}
                )
    finally:
        admin.dispose()
    return swap_db(base_url, dbname)


def worker_db_name(prefix: str = "pindb") -> str:
    return f"{prefix}_{os.environ.get('PYTEST_XDIST_WORKER', 'main')}"


# --------------------------------------------------------------------------
# Container acquisition
# --------------------------------------------------------------------------


def _wait_until_ready(url: str, timeout: float = 60.0) -> None:
    from sqlalchemy.exc import OperationalError

    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        engine = create_engine(url, connect_args={"connect_timeout": 2})
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError as err:
            last = err
            time.sleep(0.25)
        finally:
            engine.dispose()
    raise RuntimeError(f"Postgres never became ready at {url}: {last!r}")


def _host_port(container: Any, port: str = "5432/tcp") -> int:
    for _ in range(40):
        container.reload()
        bindings = container.attrs["NetworkSettings"]["Ports"].get(port)
        if bindings:
            return int(bindings[0]["HostPort"])
        time.sleep(0.25)
    raise RuntimeError(f"container {container.name} never published port {port}")


def start_kept_container() -> str:
    """
    Reattach to (or create) the long-lived ``pindb-test-pg`` container.

    Deliberately bypasses testcontainers: its Ryuk reaper removes every container
    it labels when the owning process exits, which is exactly what we are trying
    to avoid. Remove it by hand with ``docker rm -f pindb-test-pg``.
    """
    import docker
    from docker.errors import NotFound

    client = docker.from_env()
    try:
        container = client.containers.get(KEEP_CONTAINER_NAME)
        if container.status != "running":
            container.start()
    except NotFound:
        container = client.containers.run(
            PG_IMAGE,
            command=PG_COMMAND,
            name=KEEP_CONTAINER_NAME,
            detach=True,
            environment={
                "POSTGRES_USER": KEEP_USER,
                "POSTGRES_PASSWORD": KEEP_PASSWORD,
                "POSTGRES_DB": KEEP_DB,
            },
            ports={"5432/tcp": None},
        )

    port = _host_port(container)
    url = f"postgresql+psycopg://{KEEP_USER}:{KEEP_PASSWORD}@127.0.0.1:{port}/{KEEP_DB}"
    _wait_until_ready(url)
    return url


def start_throwaway_container() -> tuple[Any, str]:
    """Start a per-run Postgres container; caller stops it in ``pytest_unconfigure``."""
    from testcontainers.postgres import PostgresContainer

    container = PostgresContainer(PG_IMAGE, driver="psycopg", command=PG_COMMAND)
    container.start()
    return container, container.get_connection_url()

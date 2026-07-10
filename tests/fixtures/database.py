"""Per-worker database cloned from the shared template, engines, session patching."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from tests.fixtures import _pg, core


def pg_target(config: pytest.Config) -> tuple[str, str]:
    """
    The shared Postgres URL and template database name, published by the controller.

    Under xdist they arrive through ``workerinput``; for ``-n 0`` / ``-p no:xdist``
    there is no worker, so the controller also mirrors them into the environment.
    """
    workerinput = getattr(config, "workerinput", {})
    base_url = workerinput.get("pindb_pg_base_url") or os.environ.get(
        _pg.PG_BASE_URL_ENV
    )
    template = workerinput.get("pindb_tmpl_db") or os.environ.get(_pg.TEMPLATE_DB_ENV)
    if not base_url or not template:
        raise RuntimeError(
            "Postgres was never provisioned; the rootdir conftest decided this run "
            "needed no database. See conftest.py::_wants_db."
        )
    return base_url, template


@pytest.fixture(scope="session")
def test_engine(request: pytest.FixtureRequest) -> Generator[Engine, None, None]:
    """
    Engine bound to this worker's own database, cloned from the migrated template.

    The clone is a Postgres file copy, so no alembic run happens here.
    """
    base_url, template = pg_target(request.config)
    url = _pg.clone_template(base_url, template, _pg.worker_db_name())

    engine = create_engine(url, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def test_async_engine(test_engine: Engine) -> Generator[AsyncEngine, None, None]:
    """Async engine pointed at the same worker database as ``test_engine``."""
    import asyncio

    sync_url = test_engine.url.render_as_string(hide_password=False)
    async_url = sync_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
    async_engine = create_async_engine(async_url, poolclass=NullPool)

    yield async_engine
    asyncio.run(async_engine.dispose())


@pytest.fixture
def db_connection(test_engine: Engine) -> Generator[Connection, None, None]:
    """
    Open a single sync connection for direct DB setup/assertions in tests.
    """
    with test_engine.connect() as connection:
        yield connection


@pytest.fixture(scope="session")
def truncate_sql() -> str:
    """
    Precomputed cleanup SQL for integration tests.

    ``currencies`` cannot be preserved by omitting it: it carries AuditMixin FKs to
    ``users``, so ``TRUNCATE users ... CASCADE`` takes it along regardless. Instead
    it is restored from the FK-free copy the template build left behind — one
    server-side statement, no rows shipped from Python.
    """
    from pindb.database.base import Base

    table_names = [
        table.name
        for table in reversed(Base.metadata.sorted_tables)
        if table.name != "alembic_version"
    ]
    return (
        f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE;"
        " INSERT INTO currencies (id, name, code, created_at)"
        f" SELECT id, name, code, created_at FROM {_pg.CURRENCY_SEED_TABLE};"
    )


@pytest.fixture(autouse=True)
def patch_session_maker(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    Reconfigure the shared session_maker instance in-place.

    All route modules hold a reference to the SAME sessionmaker object, so
    configure() affects all of them without needing per-module monkeypatching.

    join_transaction_mode="create_savepoint": when a route calls
    session_maker.begin(), SQLAlchemy issues SAVEPOINT instead of BEGIN.
    On success the savepoint is released; on error it rolls back to it.
    The outer test transaction is never committed, so all writes vanish.
    """
    if core.is_unit_or_e2e_test(request=request):
        yield
        return

    db_connection: Connection = request.getfixturevalue("db_connection")
    test_async_engine: AsyncEngine = request.getfixturevalue("test_async_engine")
    cleanup_sql: str = request.getfixturevalue("truncate_sql")

    original_kw = dict(core.pindb_database.session_maker.kw)
    original_class = core.pindb_database.session_maker.class_
    original_async_kw = dict(core.pindb_database.async_session_maker.kw)

    core.pindb_database.session_maker.configure(
        bind=db_connection,
    )
    core.pindb_database.session_maker.class_ = core.AutoCommitSession
    core.pindb_database.async_session_maker.configure(bind=test_async_engine)

    yield

    core.pindb_database.session_maker.kw.clear()
    core.pindb_database.session_maker.kw.update(original_kw)
    core.pindb_database.session_maker.class_ = original_class
    core.pindb_database.async_session_maker.kw.clear()
    core.pindb_database.async_session_maker.kw.update(original_async_kw)

    db_connection.exec_driver_sql(cleanup_sql)
    db_connection.commit()

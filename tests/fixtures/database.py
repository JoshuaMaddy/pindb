"""Postgres testcontainer, engines, connection, session patching."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Generator

import pytest
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from tests.fixtures import core


@pytest.fixture(scope="session")
def pg_container():
    """Spin up a real Postgres 17 container for the entire test session."""
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:17-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def test_engine(pg_container) -> Generator[Engine, None, None]:
    """
    Create a SQLAlchemy engine pointed at the testcontainers Postgres,
    then run alembic migrations (the real ones, not create_all).
    """
    url: str = pg_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+psycopg://"
    )
    async_url: str = url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
    engine = create_engine(url, echo=False)

    env = {
        **os.environ,
        "DATABASE_CONNECTION": async_url,
        "DATABASE_CONNECTION_SYNC": url,
    }
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        env=env,
        check=True,
        cwd=str(core.REPO_ROOT),
    )

    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def test_async_engine(test_engine: Engine) -> Generator[AsyncEngine, None, None]:
    """Async engine pointed at the same testcontainer database as ``test_engine``."""
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
    """Precomputed cleanup SQL for integration tests."""
    from pindb.database.base import Base

    table_names = [
        table.name
        for table in reversed(Base.metadata.sorted_tables)
        if table.name != "alembic_version"
    ]
    return f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE"


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

    db_connection.execute(text(cleanup_sql))
    db_connection.commit()

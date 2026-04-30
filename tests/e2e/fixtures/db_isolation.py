"""Truncate entity tables between e2e tests (preserves users and sessions)."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Iterator

import pytest

_TRUNCATE_TABLES: tuple[str, ...] = (
    "change_log",
    "pending_edits",
    "user_favorite_pin_sets",
    "user_favorite_pins",
    "user_owned_pins",
    "user_wanted_pins",
    "pin_set_memberships",
    "pins_grades",
    "pins_links",
    "pins_tags",
    "pins_artists",
    "pins_shops",
    "pin_sets_links",
    "artists_links",
    "shops_links",
    "tag_implications",
    "tag_aliases",
    "shop_aliases",
    "artist_aliases",
    "links",
    "grades",
    "pins",
    "pin_sets",
    "tags",
    "artists",
    "shops",
)


def _pg_dsn() -> str:
    pg_url = os.environ.get("DATABASE_CONNECTION", "")
    return pg_url.replace("+psycopg", "")


@pytest.fixture(scope="session")
def _e2e_pg_conn(live_server):
    """One shared psycopg connection per xdist worker."""
    import psycopg

    conn = psycopg.connect(_pg_dsn())
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def db_handle(_e2e_pg_conn) -> Callable[..., list[tuple]]:
    """Tiny SQL execute helper."""

    import psycopg

    def _exec(sql: str, params: tuple[object, ...] = ()) -> list[tuple]:
        with _e2e_pg_conn.cursor() as cur:
            cur.execute(sql, params)
            try:
                rows = cur.fetchall()
            except psycopg.ProgrammingError:
                rows = []
        _e2e_pg_conn.commit()
        return rows

    return _exec


@pytest.fixture(autouse=True)
def _truncate_e2e_state(_e2e_pg_conn) -> Iterator[None]:
    yield

    import psycopg
    from psycopg import sql as pgsql

    truncate_sql = pgsql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
        pgsql.SQL(", ").join(pgsql.Identifier(t) for t in _TRUNCATE_TABLES)
    )

    last_exc: Exception | None = None
    for attempt in range(5):
        try:
            _e2e_pg_conn.rollback()
            with _e2e_pg_conn.cursor() as cur:
                cur.execute("SET LOCAL lock_timeout = '3s'")
                cur.execute(truncate_sql)
            _e2e_pg_conn.commit()
            return
        except (
            psycopg.errors.LockNotAvailable,
            psycopg.errors.DeadlockDetected,
        ) as exc:
            last_exc = exc
            _e2e_pg_conn.rollback()
            time.sleep(0.2 * (attempt + 1))
        except psycopg.Error:
            _e2e_pg_conn.rollback()
            raise
    if last_exc is not None:
        raise last_exc

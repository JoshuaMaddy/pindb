"""
Rootdir conftest — xdist parallelism and the one shared Postgres container.

This lives at the repo root rather than in ``tests/`` on purpose. ``pytest_configure``
is a historic hook, so a conftest loaded during collection (like ``tests/conftest.py``)
gets called back only *after* xdist has already decided whether to run distributed.
Only a rootdir conftest is loaded early enough to change that decision.

The controller process (never a worker) owns Postgres: it starts one container,
migrates a template database once, and hands the connection URL plus the template
name to each worker through ``workerinput``. Workers clone the template into their
own database — see ``tests/fixtures/_pg.py``.

Environment knobs (local only; CI sets neither and gets a throwaway container):

``PINDB_TEST_PG_URL``
    Use this Postgres instead of starting anything, e.g. the ``docker-compose.dev.yaml``
    server. Nothing is started or stopped.

``PINDB_TEST_KEEP_PG=1``
    Reattach to a long-lived container named ``pindb-test-pg``, creating it on first
    use and never stopping it. Combined with the alembic-head-keyed template name,
    a rerun skips both container startup and the migration chain. Tear it down with
    ``docker rm -f pindb-test-pg``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_PG_CONTAINER: pytest.StashKey = pytest.StashKey()
_PG_BASE_URL: pytest.StashKey[str] = pytest.StashKey()
_PG_TEMPLATE: pytest.StashKey[str] = pytest.StashKey()
_MEILI_CONTAINER: pytest.StashKey = pytest.StashKey()
_MEILI_URL: pytest.StashKey[str] = pytest.StashKey()

# Per-worker setup is now a ~200ms ``CREATE DATABASE ... TEMPLATE`` against a shared
# container, so workers are nearly free. The ceiling is that single Postgres server,
# not container startup — 8 is a measured starting point, not a hard limit.
MAX_AUTO_WORKERS = 8


@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_main(config: pytest.Config) -> None:
    """
    Default to parallel, bounded by ``MAX_AUTO_WORKERS``.

    ``dist`` must be set alongside ``numprocesses``: xdist only infers
    ``dist="load"`` from an explicit ``-n`` on the command line.

    Explicit ``-n N``, ``-n 0``, and ``-p no:xdist`` all still win.

    CRITICAL worker guard: xdist workers also fire ``pytest_cmdline_main``
    (``xdist/remote.py`` builds a config, sets ``config.workerinput``, then calls
    the hook) — after resetting ``numprocesses`` to ``None``. Without the
    ``workerinput`` check below, every worker re-enables distribution, becomes a
    controller, and spawns 8 more workers: an exponential fork bomb (8 → 64 →
    512 → ...). Do not remove it.
    """
    if hasattr(config, "workerinput"):
        return  # xdist worker — never re-enable distribution inside a worker
    if os.environ.get("PYTEST_XDIST_WORKER"):
        return  # belt-and-suspenders: worker env marker
    if not hasattr(config.option, "numprocesses"):
        return  # xdist not installed / disabled
    if config.option.numprocesses is not None:
        return  # caller passed -n explicitly
    config.option.numprocesses = min(MAX_AUTO_WORKERS, os.cpu_count() or 1)
    config.option.dist = "load"


def _wants_db(config: pytest.Config) -> bool:
    """
    True unless every selected path lives under ``tests/unit``.

    Unit tests never touch Postgres (``patch_session_maker`` short-circuits on them),
    so ``pytest tests/unit`` should not pay for a container — or even import
    testcontainers.
    """
    if config.option.collectonly:
        return False

    targets = [arg for arg in config.args if not arg.startswith("-")]
    if not targets:
        return True

    unit_dir = (Path(str(config.rootpath)) / "tests" / "unit").resolve()
    for target in targets:
        path = Path(target.split("::")[0])
        if not path.is_absolute():
            path = Path(str(config.rootpath)) / path
        try:
            path.resolve().relative_to(unit_dir)
        except ValueError:
            return True
    return False


def _wants_meili(config: pytest.Config) -> bool:
    """
    True only for e2e runs, which are always ``-m e2e`` (default addopts is
    ``-m "not e2e"``, so plain path selection cannot reach e2e tests).
    """
    expr = getattr(config.option, "markexpr", "") or ""
    return "e2e" in expr and "not e2e" not in expr


def pytest_configure(config: pytest.Config) -> None:
    """Controller-only: acquire Postgres and build the template database."""
    if hasattr(config, "workerinput"):
        return  # xdist worker; the controller already did this
    if not _wants_db(config):
        return

    # --import-mode=importlib does not guarantee rootdir is importable.
    if str(config.rootpath) not in sys.path:
        sys.path.insert(0, str(config.rootpath))
    from tests.fixtures import _pg

    container = None
    base_url = os.environ.get("PINDB_TEST_PG_URL")
    if base_url is None:
        if os.environ.get("PINDB_TEST_KEEP_PG") == "1":
            base_url = _pg.start_kept_container()
        else:
            container, base_url = _pg.start_throwaway_container()

    # e2e runs get the seeded user cast baked into the template (own template
    # name), so no worker has to sign anyone up or log anyone in.
    template = _pg.build_template(base_url, seed_e2e=_wants_meili(config))

    config.stash[_PG_CONTAINER] = container
    config.stash[_PG_BASE_URL] = base_url
    config.stash[_PG_TEMPLATE] = template

    # ``-n 0`` and ``-p no:xdist`` never reach pytest_configure_node, so the
    # fixtures fall back to reading these.
    os.environ[_pg.PG_BASE_URL_ENV] = base_url
    os.environ[_pg.TEMPLATE_DB_ENV] = template

    if _wants_meili(config):
        from tests.fixtures import _meili

        meili_container = None
        meili_url = os.environ.get("PINDB_TEST_MEILI_URL")
        if meili_url is None:
            if os.environ.get("PINDB_TEST_KEEP_PG") == "1":
                meili_url = _meili.start_kept_container()
            else:
                meili_container, meili_url = _meili.start_throwaway_container()

        config.stash[_MEILI_CONTAINER] = meili_container
        config.stash[_MEILI_URL] = meili_url
        os.environ[_meili.MEILI_URL_ENV] = meili_url


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node) -> None:  # type: ignore[no-untyped-def]
    """
    Hand the controller's Postgres coordinates to each xdist worker.

    ``optionalhook`` because the hookspec only exists while xdist is loaded;
    ``-p no:xdist`` would otherwise fail plugin validation.
    """
    base_url = node.config.stash.get(_PG_BASE_URL, None)
    if base_url is None:
        return  # unit-only run; no database was provisioned
    node.workerinput["pindb_pg_base_url"] = base_url
    node.workerinput["pindb_tmpl_db"] = node.config.stash[_PG_TEMPLATE]
    meili_url = node.config.stash.get(_MEILI_URL, None)
    if meili_url is not None:
        node.workerinput["pindb_meili_url"] = meili_url


def pytest_unconfigure(config: pytest.Config) -> None:
    for key in (_PG_CONTAINER, _MEILI_CONTAINER):
        container = config.stash.get(key, None)
        if container is not None:
            container.stop()

"""Shared bootstrap for integration/unit pytest fixtures (import side effects).

Must be imported before other ``tests.fixtures`` modules so ``pindb`` and
search modules load with the test image directory present.
"""

from __future__ import annotations

import importlib
import os
from csv import DictReader
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy.sql.dml import Delete, Insert, Update

# Ensure the image directory exists before pindb is imported (CONFIGURATION reads it)
os.makedirs(os.environ.get("IMAGE_DIRECTORY", "/tmp/pindb_test_images"), exist_ok=True)

# Import the app and internal modules we need to patch.
# meili_client.index() creates a Python object only — no network calls at import time.
#
# IMPORTANT: pindb/__init__.py does `from pindb.routes import search`, which sets the
# `pindb.search` ATTRIBUTE on the pindb module to `pindb.routes.search`. This shadows
# the actual pindb.search package at attribute-access level. Consequently, the `import
# pindb.search.X as alias` syntax fails because it traverses attributes (pindb → .search
# → .X) rather than using sys.modules directly.
#
# Fix: use importlib.import_module() which looks up sys.modules["pindb.search.X"]
# directly, bypassing the shadowed attribute.
import pindb.database as pindb_database  # noqa: E402
from pindb import app  # noqa: E402

_search_update = importlib.import_module("pindb.search.update")
_search_search = importlib.import_module("pindb.search.search")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CURRENCY_ROWS: list[dict[str, int | str]] | None = None


def is_unit_or_e2e_test(request) -> bool:
    return "tests" in request.node.path.parts and (
        "unit" in request.node.path.parts or "e2e" in request.node.path.parts
    )


def currency_rows() -> list[dict[str, int | str]]:
    global _CURRENCY_ROWS
    if _CURRENCY_ROWS is None:
        currencies_path = (
            REPO_ROOT / "src" / "pindb" / "database" / "data" / "currencies.csv"
        )
        with currencies_path.open(newline="") as currencies_file:
            _CURRENCY_ROWS = [
                {
                    "id": int(row["id"]),
                    "name": row["name"],
                    "code": row["code"],
                }
                for row in DictReader(currencies_file)
            ]
    return _CURRENCY_ROWS


class AutoCommitSession(Session):
    """Test session that makes fixture ``flush()`` calls visible to async routes."""

    _committing: bool = False
    _needs_commit: bool = False

    def commit(self) -> None:
        self._committing = True
        try:
            super().commit()
            self._needs_commit = False
        finally:
            self._committing = False

    def flush(self, objects=None) -> None:  # type: ignore[no-untyped-def]
        had_changes = bool(self.new or self.dirty or self.deleted)
        super().flush(objects=objects)
        if (
            (had_changes or self._needs_commit)
            and self.in_transaction()
            and not self._committing
        ):
            self.commit()

    def execute(self, statement, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = super().execute(statement, *args, **kwargs)
        if isinstance(statement, (Delete, Insert, Update)):
            self._needs_commit = True
        return result

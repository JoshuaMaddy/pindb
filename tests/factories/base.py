"""Base factory — all model factories inherit from this."""

from __future__ import annotations

from typing import Any

from factory.alchemy import SQLAlchemyModelFactory

# Holds the current test's db_session. Set by the bind_factories autouse fixture
# in conftest.py before each test, cleared afterward.
_current_session: Any = None


class BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"

    @classmethod
    def _meta_session(cls):
        return _current_session

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Ensure the factory always uses the current test session
        cls._meta.sqlalchemy_session = _current_session  # type: ignore[assignment]  # ty:ignore[unresolved-attribute]
        return super()._create(model_class, *args, **kwargs)

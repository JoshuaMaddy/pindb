"""Custom SQLAlchemy column types (Pydantic-validated JSONB)."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import TypeAdapter
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

_ValueType = TypeVar("_ValueType")


class PydanticJSON(TypeDecorator[_ValueType], Generic[_ValueType]):
    """Postgres ``JSONB`` column whose Python value is a validated Pydantic object.

    The column is bound to a :class:`pydantic.TypeAdapter` (over a model, a
    discriminated union, or any type an adapter accepts). Values are serialized to
    JSON-safe primitives on write and re-validated into typed instances on read.
    Postgres-only, matching the codebase's direct use of ``JSONB`` elsewhere.

    ``cache_ok`` is ``False`` because the bound adapter is an arbitrary object that
    does not participate in SQLAlchemy's statement cache-key generation; the only
    cost is skipping compiled-statement caching for columns of this type.
    """

    impl = JSONB
    cache_ok = False

    def __init__(
        self,
        adapter: TypeAdapter[_ValueType],
        **kwargs: object,
    ) -> None:
        """Bind the column to *adapter*.

        Args:
            adapter (TypeAdapter): Validates and serializes column values.
            **kwargs (object): Forwarded to :class:`TypeDecorator`.
        """
        super().__init__(**kwargs)
        self._adapter: TypeAdapter[_ValueType] = adapter

    def process_bind_param(
        self,
        value: _ValueType | None,
        dialect: Dialect,
    ) -> object | None:
        """Serialize *value* to JSON-safe primitives for storage."""
        if value is None:
            return None
        return self._adapter.dump_python(
            value,
            mode="json",
        )

    def process_result_value(
        self,
        value: object | None,
        dialect: Dialect,
    ) -> _ValueType | None:
        """Validate the stored JSON back into the typed Pydantic value."""
        if value is None:
            return None
        return self._adapter.validate_python(value)

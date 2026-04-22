"""Shared alias-replacement helper for tag/artist/shop alias rows.

``(entity_id, alias)`` is unique on each ``*_aliases`` table. Assigning new
instances directly can flush INSERTs before DELETEs on the old rows, causing
a duplicate-key error when an alias string is unchanged. Delete and flush
first, then attach replacements.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, TypeVar

from sqlalchemy.orm import Session

AliasT = TypeVar("AliasT")


def replace_aliases(
    *,
    owner: Any,
    alias_cls: type[AliasT],
    raw_aliases: Iterable[str],
    session: Session,
    normalizer: Callable[[str], str] | None = None,
) -> None:
    """Replace ``owner.aliases`` with deduped, cleaned ``alias_cls`` instances.

    ``normalizer`` defaults to ``str.strip``; tags pass ``normalize_tag_name``.
    """
    clean: Callable[[str], str] = normalizer or (lambda raw: raw.strip())
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in raw_aliases:
        value = clean(raw)
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    for existing in list(owner.aliases):
        session.delete(existing)
    session.flush()
    owner.aliases = [alias_cls(alias=value) for value in cleaned]

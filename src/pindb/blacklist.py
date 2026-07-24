"""Fuzzy matching of entered Shop/Artist names against the do-not-index blacklist.

The blacklist (``database/blacklist.py``) holds names real-world shops/artists
asked us not to catalog. Exact matches (same normalized key as the entities'
generated ``normalized_name`` columns) are hard-blocked server-side; fuzzy
matches only produce an inline warning — the editor may still submit when
certain the name is unrelated.

The list is expected to stay tiny (tens of rows), so matching loads every row
for the entity type and scores in Python with rapidfuzz.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from fastapi import Request
from fastapi.responses import HTMLResponse
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.database import BlacklistedName, BlacklistEntityType, async_session_maker
from pindb.htmx_toast import unique_constraint_response

# WRatio score (0-100) at or above which a candidate counts as "similar".
# High enough that generic single-word names don't warn constantly, low enough
# to catch typos, spacing and small suffix variants ("X Studio" vs "X Studios").
BLACKLIST_FUZZY_THRESHOLD: float = 87.0


@dataclass(frozen=True)
class BlacklistMatch:
    """A candidate name that matched a blacklist entry.

    Args:
        candidate (str): The user-entered name that matched.
        entry_name (str): The blacklisted name it matched against.
        entity_type (BlacklistEntityType): Which entity kind the entry blocks.
        exact (bool): Whether the normalized keys are identical (hard block).
        score (float): rapidfuzz WRatio score (100.0 for exact matches).
    """

    candidate: str
    entry_name: str
    entity_type: BlacklistEntityType
    exact: bool
    score: float


def _fuzz_key(name: str) -> str:
    """Return the whitespace-collapsed lowercase key used for fuzzy scoring."""
    return " ".join(name.lower().split())


def _exact_key(name: str) -> str:
    """Return the exact-match key: the entity ``normalized_name`` canon, but
    with runs of whitespace collapsed first — "Sample  Shop" must not slip past
    a block on "Sample Shop" via a double space."""
    return "_".join(name.lower().split())


def match_blacklisted_names(
    *,
    candidates: Iterable[str],
    entries: Sequence[BlacklistedName],
) -> BlacklistMatch | None:
    """Score candidate names against blacklist entries.

    Args:
        candidates (Iterable[str]): User-entered names (primary name + aliases).
        entries (Sequence[BlacklistedName]): Blacklist rows for one entity type.

    Returns:
        BlacklistMatch | None: An exact match if any candidate's normalized key
            equals an entry's, else the highest-scoring fuzzy match at or above
            :data:`BLACKLIST_FUZZY_THRESHOLD`, else ``None``.
    """
    best_fuzzy: BlacklistMatch | None = None

    for candidate in candidates:
        normalized_candidate: str = _exact_key(name=candidate)
        if not normalized_candidate:
            continue

        for entry in entries:
            # Computed from ``name`` (not the generated ``normalized_name``
            # column) so unflushed instances (unit tests) match too.
            if normalized_candidate == _exact_key(name=entry.name):
                return BlacklistMatch(
                    candidate=candidate,
                    entry_name=entry.name,
                    entity_type=entry.entity_type,
                    exact=True,
                    score=100.0,
                )

            score: float = fuzz.WRatio(
                _fuzz_key(name=candidate),
                _fuzz_key(name=entry.name),
            )
            if score >= BLACKLIST_FUZZY_THRESHOLD and (
                best_fuzzy is None or score > best_fuzzy.score
            ):
                best_fuzzy = BlacklistMatch(
                    candidate=candidate,
                    entry_name=entry.name,
                    entity_type=entry.entity_type,
                    exact=False,
                    score=score,
                )

    return best_fuzzy


async def find_blacklist_match(
    *,
    session: AsyncSession,
    entity_type: BlacklistEntityType,
    candidates: Iterable[str],
) -> BlacklistMatch | None:
    """Load the blacklist for ``entity_type`` and match ``candidates`` against it."""
    entries: Sequence[BlacklistedName] = (
        await session.scalars(
            select(BlacklistedName).where(
                BlacklistedName.entity_type == entity_type,
            )
        )
    ).all()
    if not entries:
        return None
    return match_blacklisted_names(candidates=candidates, entries=entries)


def blacklist_block_message(*, match: BlacklistMatch) -> str:
    """User-facing message for a hard-blocked (exact) blacklist match."""
    kind_label: str = (
        "Shop" if match.entity_type == BlacklistEntityType.shop else "Artist"
    )
    return f'"{match.entry_name}" {kind_label} is not indexable at their request.'


async def blacklisted_exact_match_response(
    *,
    request: Request,
    entity_type: BlacklistEntityType,
    candidates: Iterable[str],
) -> HTMLResponse | None:
    """Return the block response when a candidate exactly matches the blacklist.

    Route helper for create/edit POST handlers: opens its own read session,
    checks name + aliases, and returns the standard conflict toast (HTMX) or
    409 (full-page) on an **exact** match. Fuzzy matches never block here —
    they only warn inline via the check-name endpoint.

    Returns:
        HTMLResponse | None: The response to return, or ``None`` to proceed.
    """
    async with async_session_maker() as session:
        match: BlacklistMatch | None = await find_blacklist_match(
            session=session,
            entity_type=entity_type,
            candidates=candidates,
        )
    if match is None or not match.exact:
        return None
    return unique_constraint_response(
        request=request,
        message=blacklist_block_message(match=match),
    )

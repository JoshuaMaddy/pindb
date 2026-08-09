"""
Unit tests for the pending queue's day-grouped, name-alphabetised ordering.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from pindb.database.pending_mixin import PendingAuditEntity
from pindb.routes._pending_sort import sort_pending_entities


@dataclass
class _Row:
    """Minimal stand-in for a pending entity (only ``id``/``name``/``created_at``)."""

    id: int
    name: str
    created_at: datetime | None


def _sorted_names(rows: list[_Row]) -> list[str]:
    entities: list[PendingAuditEntity] = cast(list[PendingAuditEntity], rows)
    return [cast(_Row, entity).name for entity in sort_pending_entities(items=entities)]


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 7, day, hour, minute, tzinfo=UTC)


def test_newest_day_first_then_alphabetical() -> None:
    rows: list[_Row] = [
        _Row(id=1, name="zebra", created_at=_at(day=10, hour=9)),
        _Row(id=2, name="apple", created_at=_at(day=10, hour=17)),
        _Row(id=3, name="mango", created_at=_at(day=11, hour=8)),
        _Row(id=4, name="Banana", created_at=_at(day=11, hour=20)),
    ]
    assert _sorted_names(rows=rows) == ["Banana", "mango", "apple", "zebra"]


def test_midnight_straddle_stays_one_group() -> None:
    rows: list[_Row] = [
        _Row(id=1, name="zebra", created_at=_at(day=10, hour=23, minute=58)),
        _Row(id=2, name="apple", created_at=_at(day=11, hour=0, minute=6)),
    ]
    assert _sorted_names(rows=rows) == ["apple", "zebra"]


def test_distant_times_across_midnight_stay_separate() -> None:
    rows: list[_Row] = [
        _Row(id=1, name="zebra", created_at=_at(day=10, hour=9)),
        _Row(id=2, name="apple", created_at=_at(day=11, hour=18)),
    ]
    assert _sorted_names(rows=rows) == ["apple", "zebra"]


def test_bridge_extends_at_most_one_day() -> None:
    """A trickle every three hours must not fuse a whole week into one group."""
    rows: list[_Row] = [
        _Row(
            id=index,
            name=f"pin-{index:02d}",
            created_at=_at(day=10, hour=0) + timedelta(hours=3 * index),
        )
        for index in range(24)
    ]
    ordered: list[str] = _sorted_names(rows=rows)
    # The newest group bridges exactly two days (pin-23 .. pin-08) and stops;
    # the older days form their own group instead of fusing into one block.
    assert ordered[:16] == sorted(f"pin-{index:02d}" for index in range(8, 24))
    assert ordered[16:] == sorted(f"pin-{index:02d}" for index in range(0, 8))


def test_undated_rows_sort_last() -> None:
    rows: list[_Row] = [
        _Row(id=1, name="zebra", created_at=None),
        _Row(id=2, name="apple", created_at=None),
        _Row(id=3, name="mango", created_at=_at(day=10, hour=9)),
    ]
    assert _sorted_names(rows=rows) == ["mango", "apple", "zebra"]

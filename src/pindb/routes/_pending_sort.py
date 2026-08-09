"""
Ordering for the admin pending queue's created-entity sections.

The queue is read as "what came in, batch by batch", so entries are grouped by
the day they were submitted (newest day first) and alphabetised inside that day.
A strict calendar-day key splits one sitting in two whenever it straddles
midnight, so adjacent days are merged when the entries either side of the
boundary are close enough in time to be the same batch (``CLUSTER_GAP``).
"""

from collections.abc import Sequence
from datetime import date, datetime, timedelta

from pindb.database.pending_mixin import PendingAuditEntity

# Two entries on either side of a day boundary belong to the same group when
# they are no further apart than this — 23:58 and 00:04 is one sitting, not two.
CLUSTER_GAP: timedelta = timedelta(hours=4)


def _sort_name(entity: PendingAuditEntity) -> str:
    """Display name used for the alphabetical tiebreak within a day group."""
    name: object = getattr(entity, "display_name", None) or getattr(
        entity, "name", None
    )
    return name.casefold() if isinstance(name, str) else ""


def _day(moment: datetime) -> date:
    return moment.date()


def sort_pending_entities(
    items: Sequence[PendingAuditEntity],
) -> list[PendingAuditEntity]:
    """Order pending entries newest-day-first, then by name inside each day.

    Entries whose ``created_at`` is unset sort last, alphabetically among
    themselves — an audit column that never got written is not a date.

    Args:
        items (Sequence[PendingAuditEntity]): Pending entries of one entity type.

    Returns:
        list[PendingAuditEntity]: A new list in queue order.
    """
    dated: list[PendingAuditEntity] = [
        entity for entity in items if entity.created_at is not None
    ]
    undated: list[PendingAuditEntity] = [
        entity for entity in items if entity.created_at is None
    ]

    # Newest first, so groups are built walking backwards in time.
    dated.sort(key=lambda entity: (entity.created_at, entity.id), reverse=True)  # type: ignore[arg-type,return-value]

    groups: list[list[PendingAuditEntity]] = []
    group_days: set[date] = set()
    previous: datetime | None = None
    for entity in dated:
        created_at: datetime = entity.created_at  # type: ignore[assignment]
        day: date = _day(moment=created_at)
        # A group is one day, optionally extended once backwards over a midnight
        # the batch happened to straddle. Capping the bridge at a single extra
        # day stops a steady trickle of submissions from fusing a whole week
        # into one alphabetised block.
        same_group: bool = previous is not None and (
            day in group_days
            or (len(group_days) == 1 and previous - created_at <= CLUSTER_GAP)
        )
        if same_group and groups:
            groups[-1].append(entity)
            group_days.add(day)
        else:
            groups.append([entity])
            group_days = {day}
        previous = created_at

    ordered: list[PendingAuditEntity] = []
    for group in groups:
        group.sort(key=lambda entity: (_sort_name(entity=entity), entity.id))
        ordered.extend(group)

    undated.sort(key=lambda entity: (_sort_name(entity=entity), entity.id))
    ordered.extend(undated)
    return ordered

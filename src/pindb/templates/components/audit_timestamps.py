"""
htpy page and fragment builders: `templates/components/audit_timestamps.py`.
"""

from datetime import datetime

from htpy import Fragment, fragment, span
from htpy import time as time_el


def _local_time(dt: datetime) -> Fragment:
    return fragment[
        time_el(
            datetime=dt.isoformat() + "Z",
            data_localtime=True,
        )["…"]
    ]


def audit_timestamps(
    created_at: datetime | None, updated_at: datetime | None
) -> Fragment:
    """Subtle one-line row showing created/updated timestamps, localized client-side."""
    return fragment[
        span(class_="text-xs text-lightest-hover")[
            created_at and "Added ",
            created_at and _local_time(created_at),
            updated_at and " · Updated ",
            updated_at and _local_time(updated_at),
        ]
    ]

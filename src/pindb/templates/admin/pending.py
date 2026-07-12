"""
htpy page and fragment builders: `templates/admin/pending.py`.
"""

from datetime import datetime

from fastapi import Request
from htpy import Element, div, p, span
from htpy import time as time_el

from pindb.database.artist import Artist
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_mixin import PendingAuditEntity
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.database.user import User
from pindb.templates.admin.pending_bulk import BulkGroupView, _bulk_groups_section
from pindb.templates.admin.pending_entities import _sections
from pindb.templates.admin.pending_needs_changes import NeedsChangesView
from pindb.templates.base import html_base
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading


def _local_date(dt: datetime | None) -> Element | str:
    if dt is None:
        return "—"
    return time_el(datetime=dt.isoformat() + "Z", data_localtime=True)["…"]


def pending_content(
    pending_pins: list[Pin],
    pending_shops: list[Shop],
    pending_artists: list[Artist],
    pending_tags: list[Tag],
    pending_pin_sets: list[PinSet],
    creators: dict[int, User],
    edit_groups: dict[tuple[str, int], list[PendingEdit]] | None = None,
    edit_group_entities: dict[tuple[str, int], PendingAuditEntity] | None = None,
    bulk_groups: list[BulkGroupView] | None = None,
    needs_changes: NeedsChangesView | None = None,
) -> Element:
    """The swappable region of the pending queue.

    Action buttons ``hx-post`` and swap ``#pending-content`` with a fresh copy
    of this fragment, so a single approve/reject/delete updates every section
    (including cascaded dependency rows) and the count badges in place — no
    full-page navigation, so the scroll position is preserved.
    """
    edit_groups = edit_groups or {}
    edit_group_entities = edit_group_entities or {}
    bulk_groups = bulk_groups or []
    needs_changes = needs_changes or NeedsChangesView()
    # The heading count is the admin's workload, so needs-changes entries are left
    # out — they are waiting on their submitter, and counting them here would keep
    # the badge permanently above zero. Matches routes/admin/_pending_count.py.
    total = (
        len(pending_pins)
        + len(pending_shops)
        + len(pending_artists)
        + len(pending_tags)
        + len(pending_pin_sets)
        + len(edit_groups)
        + len(bulk_groups)
    )

    return div(id="pending-content", class_="flex flex-col gap-2")[
        div(class_="flex items-baseline gap-3")[
            page_heading(icon="clock", text="Pending Approvals"),
            span(
                class_="text-xs font-semibold px-2 py-0.5 rounded bg-pending-dark-hover text-pending-main-hover"
            )[str(total)],
        ],
        p(class_="text-lightest-hover text-sm")[
            "Review and approve or reject pending entries submitted by editors. "
            "Approving a pin also approves its pending dependencies (shops, artists, tags)."
        ],
        *_sections(
            pending_pins=pending_pins,
            pending_shops=pending_shops,
            pending_artists=pending_artists,
            pending_tags=pending_tags,
            pending_pin_sets=pending_pin_sets,
            creators=creators,
            edit_groups=edit_groups,
            edit_group_entities=edit_group_entities,
            bulk_groups=bulk_groups,
            needs_changes=needs_changes,
            local_date_formatter=_local_date,
            bulk_groups_section=_bulk_groups_section,
        ),
    ]


def pending_page(
    request: Request,
    pending_pins: list[Pin],
    pending_shops: list[Shop],
    pending_artists: list[Artist],
    pending_tags: list[Tag],
    pending_pin_sets: list[PinSet],
    creators: dict[int, User],
    edit_groups: dict[tuple[str, int], list[PendingEdit]] | None = None,
    edit_group_entities: dict[tuple[str, int], PendingAuditEntity] | None = None,
    bulk_groups: list[BulkGroupView] | None = None,
    needs_changes: NeedsChangesView | None = None,
) -> Element:
    return html_base(
        title="Pending Approvals",
        request=request,
        body_content=centered_div(
            content=pending_content(
                pending_pins=pending_pins,
                pending_shops=pending_shops,
                pending_artists=pending_artists,
                pending_tags=pending_tags,
                pending_pin_sets=pending_pin_sets,
                creators=creators,
                edit_groups=edit_groups,
                edit_group_entities=edit_group_entities,
                bulk_groups=bulk_groups,
                needs_changes=needs_changes,
            ),
            flex=True,
            col=True,
        ),
    )

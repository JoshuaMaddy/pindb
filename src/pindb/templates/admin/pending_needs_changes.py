"""
Pending admin page section for entries a reviewer sent back for changes.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from htpy import Element, a, div, p, span, td, tr

from pindb.database.entity_type import EntityType
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_mixin import PendingAuditEntity
from pindb.database.user import User
from pindb.templates.admin._pending_shared import (
    action_buttons,
    action_form_button,
    pending_table,
    section_header,
)
from pindb.utils import pretty_titlecase

# Name / Type / Submitted by / Requested changes / Actions. No "Request changes"
# button here, so Actions only has to fit Approve + Delete.
_COL_WIDTHS: tuple[str | None, ...] = (None, "6rem", "9rem", "22rem", "13rem")


@dataclass
class NeedsChangesView:
    """Everything a reviewer sent back, entities and edit chains alike."""

    entities: list[tuple[str, PendingAuditEntity]] = field(default_factory=list)
    edits: dict[tuple[str, int], list[PendingEdit]] = field(default_factory=dict)
    edit_entities: dict[tuple[str, int], PendingAuditEntity] = field(
        default_factory=dict
    )

    def __len__(self) -> int:
        return len(self.entities) + len(self.edits)


def _reason_cell(reason: str | None) -> Element:
    return td(class_="py-2 pr-6 text-lightest-hover text-xs whitespace-pre-line")[
        reason or "—"
    ]


def needs_changes_section(
    *,
    view: NeedsChangesView,
    creators: dict[int, User],
    local_date_formatter: Callable[[datetime | None], Element | str],
) -> Element:
    """Entries waiting on their submitter rather than on an admin.

    They keep Approve and Delete: a reviewer can change their mind, or bin an entry
    that is never going to be salvageable. There is no second "Request changes" —
    the entry is already flagged, and the submitter has the feedback.
    """
    rows: list[Element] = [
        _entity_row(
            entity_type_slug=entity_type_slug,
            entity=entity,
            creators=creators,
            local_date_formatter=local_date_formatter,
        )
        for entity_type_slug, entity in view.entities
    ]
    rows.extend(
        _edit_row(
            table_name=table_name,
            entity_id=entity_id,
            chain=chain,
            entity=view.edit_entities.get((table_name, entity_id)),
            creators=creators,
            local_date_formatter=local_date_formatter,
        )
        for (table_name, entity_id), chain in sorted(view.edits.items())
    )

    return div(class_="flex flex-col gap-2")[
        section_header(
            icon="message-square-warning", title="Needs Changes", count=len(view)
        ),
        p(class_="text-lightest-hover text-sm")[
            "Entries sent back to their submitter with a change request. They stay "
            "visible to the submitter, who can edit and resubmit — which returns the "
            "entry to the pending queue above."
        ],
        pending_table(
            columns=[
                "Name",
                "Type",
                "Submitted by",
                "Requested changes",
                "Actions",
            ],
            col_widths=_COL_WIDTHS,
            rows=rows,
        ),
    ]


def _creator_name(creator_id: int | None, creators: dict[int, User]) -> str:
    creator = creators.get(creator_id) if creator_id else None
    return creator.username if creator else "—"


def _entity_row(
    *,
    entity_type_slug: str,
    entity: PendingAuditEntity,
    creators: dict[int, User],
    local_date_formatter: Callable[[datetime | None], Element | str],
) -> Element:
    name: str = getattr(entity, "name", f"#{entity.id}")
    approve_url = f"/admin/pending/approve/{entity_type_slug}/{entity.id}"
    delete_url = f"/admin/pending/delete/{entity_type_slug}/{entity.id}"

    return tr(class_="border-b border-darker hover:bg-main-hover")[
        td(class_="py-2 pr-6")[
            a(href=f"/get/{entity_type_slug}/{entity.id}")[name],
            span(class_="block text-xs text-lighter-hover")[
                "Sent back ", local_date_formatter(entity.rejected_at)
            ],
        ],
        td(class_="py-2 pr-6 text-lighter-hover text-xs")[
            pretty_titlecase(entity_type_slug.replace("_", " "))
        ],
        td(class_="py-2 pr-6 text-lighter-hover")[
            _creator_name(entity.created_by_id, creators)
        ],
        _reason_cell(entity.rejection_reason),
        td(class_="py-2")[
            action_buttons(
                action_form_button(action="approve", url=approve_url),
                action_form_button(action="delete", url=delete_url),
            )
        ],
    ]


def _edit_row(
    *,
    table_name: str,
    entity_id: int,
    chain: list[PendingEdit],
    entity: PendingAuditEntity | None,
    creators: dict[int, User],
    local_date_formatter: Callable[[datetime | None], Element | str],
) -> Element:
    entity_type = EntityType.from_table_name(table_name)
    slug: str = entity_type.slug if entity_type is not None else table_name
    name: str = getattr(entity, "name", f"#{entity_id}") if entity else f"#{entity_id}"
    latest = chain[-1] if chain else None

    approve_url = f"/admin/pending/approve-edits/{slug}/{entity_id}"
    delete_url = f"/admin/pending/delete-edits/{slug}/{entity_id}"

    return tr(class_="border-b border-darker hover:bg-main-hover")[
        td(class_="py-2 pr-6")[
            a(href=f"/get/{slug}/{entity_id}?version=pending")[name],
            span(class_="block text-xs text-lighter-hover")[
                f"{len(chain)} edit(s) — sent back ",
                local_date_formatter(latest.rejected_at if latest else None),
            ],
        ],
        td(class_="py-2 pr-6 text-lighter-hover text-xs")["Edit"],
        td(class_="py-2 pr-6 text-lighter-hover")[
            _creator_name(latest.created_by_id if latest else None, creators)
        ],
        _reason_cell(latest.rejection_reason if latest else None),
        td(class_="py-2")[
            action_buttons(
                action_form_button(
                    action="approve", url=approve_url, title="Approve edits"
                ),
                action_form_button(
                    action="delete", url=delete_url, title="Delete edits"
                ),
            )
        ],
    ]

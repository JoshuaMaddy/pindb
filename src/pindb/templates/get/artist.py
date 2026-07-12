"""
htpy page and fragment builders: `templates/get/artist.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element, code, fragment

from pindb.database import Artist, User
from pindb.database.entity_type import EntityType
from pindb.database.pending_edit_utils import PendingChange
from pindb.database.pin import Pin
from pindb.routes._urls import artist_url
from pindb.templates.base import html_base
from pindb.templates.components.dialogs.confirm_modal import confirm_modal
from pindb.templates.components.display.audit_timestamps import audit_timestamps
from pindb.templates.components.display.changes_requested_banner import (
    changes_requested_banner,
)
from pindb.templates.components.display.description_block import description_block
from pindb.templates.components.display.entity_links import entity_links
from pindb.templates.components.display.linked_items_row import linked_items_row
from pindb.templates.components.display.pending_changes_table import (
    pending_changes_table,
)
from pindb.templates.components.display.pending_edit_banner import pending_edit_banner
from pindb.templates.components.display.review_actions import review_actions_bar
from pindb.templates.components.forms.icon_button import icon_button
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading
from pindb.templates.components.nav.bread_crumb import bread_crumb
from pindb.templates.components.pins.paginated_pin_grid import paginated_pin_grid
from pindb.templates.components.seo.opengraph import opengraph_head
from pindb.utils import review_label


def artist_page(
    request: Request,
    artist: Artist,
    pins: Sequence[Pin],
    total_count: int,
    page: int,
    per_page: int,
    has_pending_chain: bool = False,
    viewing_pending: bool = False,
    pending_changes: Sequence[PendingChange] = (),
    edit_change_request: str | None = None,
) -> Element:
    user: User | None = getattr(getattr(request, "state", None), "user", None)
    canonical_url = str(artist_url(request=request, artist=artist))
    # An admin looking at an unapproved entry rules on it from the review bar, which
    # carries its own Delete. The heading's Delete posts to /delete/{type}/{id},
    # which cannot even see an unapproved row (the ORM filter hides it), so leaving
    # it up would offer a second, silently broken Delete.
    in_review: bool = (
        user is not None and user.is_admin and (artist.is_pending or artist.is_rejected)
    )
    pending_url = canonical_url + "?version=pending"
    return html_base(
        title=artist.name,
        request=request,
        head_content=opengraph_head(
            title=f"Artist: {artist.name}",
            description=f"View pins by {artist.name} on PinDB.",
            canonical_url=canonical_url,
            image_url=str(
                request.url_for("get_og_image", entity_type="artist", id=artist.id)
            ),
        ),
        body_content=centered_div(
            content=[
                bread_crumb(
                    entries=[
                        (request.url_for("get_list_index"), "List"),
                        (request.url_for("get_list_artists"), "Artists"),
                        review_label(
                            artist.name,
                            is_pending=artist.is_pending,
                            is_rejected=artist.is_rejected,
                        ),
                    ]
                ),
                artist.is_rejected
                and changes_requested_banner(
                    reason=artist.rejection_reason,
                    edit_url=str(request.url_for("get_edit_artist", id=artist.id)),
                ),
                edit_change_request
                and changes_requested_banner(
                    reason=edit_change_request,
                    edit_url=str(request.url_for("get_edit_artist", id=artist.id)),
                    is_edit=True,
                ),
                has_pending_chain
                and not edit_change_request
                and pending_edit_banner(
                    viewing_pending=viewing_pending,
                    canonical_url=canonical_url,
                    pending_url=pending_url,
                ),
                viewing_pending and pending_changes_table(pending_changes),
                in_review
                and review_actions_bar(
                    entity_type=EntityType.artist,
                    entity_id=artist.id,
                    entity_name=artist.name,
                    is_rejected=artist.is_rejected,
                ),
                page_heading(
                    icon="palette",
                    text=review_label(
                        artist.name,
                        is_pending=artist.is_pending,
                        is_rejected=artist.is_rejected,
                    ),
                    full_width=True,
                    extras=fragment[
                        user
                        and (user.is_admin or user.is_editor)
                        and icon_button(
                            icon="layers",
                            title="Bulk edit this artist's pins",
                            href=f"/bulk-edit/from/artist/{artist.id}",
                        ),
                        user
                        and (user.is_admin or user.is_editor)
                        and icon_button(
                            icon="pen",
                            title="Edit artist",
                            href=str(request.url_for("get_edit_artist", id=artist.id)),
                        ),
                        user
                        and user.is_admin
                        and not in_review
                        and confirm_modal(
                            trigger=icon_button(
                                icon="trash-2",
                                title="Delete artist",
                                variant="danger",
                            ),
                            message=f'Delete the artist "{artist.name}"?',
                            form_action=str(
                                request.url_for(
                                    "post_delete_entity",
                                    entity_type="artist",
                                    id=artist.id,
                                )
                            ),
                        ),
                    ],
                ),
                description_block(artist.description),
                audit_timestamps(
                    created_at=artist.created_at,
                    updated_at=artist.updated_at,
                ),
                bool(artist.aliases)
                and linked_items_row(
                    icon="arrow-left-right",
                    label="Also known as",
                    items=[
                        code(
                            class_="bg-darker text-base-text rounded px-1.5 py-0.5 text-sm font-mono"
                        )[a.alias]
                        for a in sorted(artist.aliases, key=lambda a: a.alias)
                    ],
                ),
                entity_links(artist.links),
                paginated_pin_grid(
                    request=request,
                    pins=pins,
                    total_count=total_count,
                    page=page,
                    page_url=str(artist_url(request=request, artist=artist)),
                    per_page=per_page,
                ),
            ],
            flex=True,
            col=True,
        ),
    )

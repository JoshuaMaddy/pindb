"""
htpy page and fragment builders: `templates/get/artist.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element, a, br, code, div, fragment, h2

from pindb.database import Artist, User
from pindb.database.pin import Pin
from pindb.routes._urls import artist_url
from pindb.templates.base import html_base
from pindb.templates.components.dialogs.confirm_modal import confirm_modal
from pindb.templates.components.display.audit_timestamps import audit_timestamps
from pindb.templates.components.display.description_block import description_block
from pindb.templates.components.display.linked_items_row import linked_items_row
from pindb.templates.components.display.pending_edit_banner import pending_edit_banner
from pindb.templates.components.forms.icon_button import icon_button
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading
from pindb.templates.components.nav.bread_crumb import bread_crumb
from pindb.templates.components.pins.paginated_pin_grid import paginated_pin_grid
from pindb.templates.components.seo.opengraph import opengraph_head


def artist_page(
    request: Request,
    artist: Artist,
    pins: Sequence[Pin],
    total_count: int,
    page: int,
    per_page: int,
    has_pending_chain: bool = False,
    viewing_pending: bool = False,
) -> Element:
    user: User | None = getattr(getattr(request, "state", None), "user", None)
    canonical_url = str(artist_url(request=request, artist=artist))
    pending_url = canonical_url + "?version=pending"
    return html_base(
        title=artist.name,
        request=request,
        head_content=opengraph_head(
            title=f"Artist: {artist.name}",
            description=f"Pins by {artist.name} on PinDB.",
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
                        ("(P) " + artist.name) if artist.is_pending else artist.name,
                    ]
                ),
                has_pending_chain
                and pending_edit_banner(
                    viewing_pending=viewing_pending,
                    canonical_url=canonical_url,
                    pending_url=pending_url,
                ),
                page_heading(
                    icon="palette",
                    text=("(P) " + artist.name) if artist.is_pending else artist.name,
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
                fragment[
                    bool(len(artist.links))
                    and div[
                        h2["Links"],
                        *[
                            fragment[a(href=link.path)[link.path], br]
                            for link in artist.links
                        ],
                    ]
                ],
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

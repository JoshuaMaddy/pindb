"""
htpy page and fragment builders: `templates/get/tag.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element, code, div, fragment, i, p, span
from titlecase import titlecase

from pindb.database import User
from pindb.database.pin import Pin
from pindb.database.tag import Tag
from pindb.routes._urls import tag_url
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
from pindb.templates.components.nav.pill_link import pill_link
from pindb.templates.components.pins.paginated_pin_grid import paginated_pin_grid
from pindb.templates.components.seo.opengraph import opengraph_head
from pindb.templates.components.tags.tag_branding import (
    CATEGORY_COLORS,
    CATEGORY_HOVER_CLASSES,
    CATEGORY_ICONS,
    category_badge,
)

_RELATION_CAP = 5


def _relation_pills(tags: list[Tag], request: Request) -> list[Element]:
    return [
        pill_link(
            href=str(tag_url(request=request, tag=t)),
            text=("(P) " + t.display_name) if t.is_pending else t.display_name,
            icon=CATEGORY_ICONS.get(t.category, "tag"),
            color_classes=CATEGORY_COLORS.get(t.category, "bg-main text-base-text"),
            hover_classes=CATEGORY_HOVER_CLASSES.get(
                t.category, "hover:border-accent hover:text-accent"
            ),
        )
        for t in sorted(tags, key=lambda t: (t.category, t.name))
    ]


def tag_relation_items(
    tags: list[Tag],
    request: Request,
    tag_id: int,
    direction: str,
    collapsed: bool = True,
) -> Element:
    pills = _relation_pills(tags, request)
    target_id = f"tag-{direction}-items-{tag_id}"
    if collapsed and len(pills) > _RELATION_CAP:
        expand_url = str(
            request.url_for("get_tag_relations", id=tag_id, direction=direction)
        )
        expand_btn = span(
            hx_get=expand_url,
            hx_target=f"#{target_id}",
            hx_swap="outerHTML",
            role="button",
            aria_label="Show all",
            class_="cursor-pointer text-sm text-lightest-hover hover:text-accent px-1",
        )["…"]
        return div(id=target_id, class_="contents")[*pills[:_RELATION_CAP], expand_btn]
    return div(id=target_id, class_="contents")[*pills]


def tag_implication_preview(resolved: set[Tag], selected: set[Tag]) -> Element:
    """HTMX fragment: shows source→implied pairs for tags not already selected."""
    pairs: list[tuple[Tag, set[Tag]]] = sorted(
        [
            (tag, tag.implications - selected)
            for tag in selected
            if tag.implications - selected
        ],
        key=lambda p: p[0].name,
    )

    if not pairs:
        return div()

    def _badge(tag: Tag, implied: bool = False) -> Element:
        color = CATEGORY_COLORS.get(tag.category, "bg-tag-general text-tag-general-fg")
        icon_name = CATEGORY_ICONS.get(tag.category, "tag")
        extra = "opacity-60 ring-1 ring-inset ring-white/20" if implied else ""
        return span(
            class_=f"inline-flex items-center gap-1 p-1.5 rounded text-xs {color} {extra}",
            title=titlecase(tag.category.value),
        )[
            i(data_lucide=icon_name, class_=f"w-4 h-4 shrink-0 {color}"),
            tag.display_name,
        ]

    return div(class_="flex flex-col gap-1 mt-1")[
        p(class_="text-xs text-lightest-hover font-semibold")["Tag parents:"],
        div(class_="flex flex-col gap-1")[
            [
                div(class_="flex items-center flex-wrap gap-1")[
                    _badge(source),
                    span(class_="text-lightest-hover text-xs")["→"],
                    [
                        _badge(t, implied=True)
                        for t in sorted(new_implied, key=lambda t: t.name)
                    ],
                ]
                for source, new_implied in pairs
            ]
        ],
    ]


def tag_page(
    request: Request,
    tag: Tag,
    pins: Sequence[Pin],
    total_count: int,
    page: int,
    per_page: int,
    has_pending_chain: bool = False,
    viewing_pending: bool = False,
) -> Element:
    user: User | None = getattr(getattr(request, "state", None), "user", None)
    display_name = ("(P) " + tag.display_name) if tag.is_pending else tag.display_name
    canonical_url = str(tag_url(request=request, tag=tag))
    pending_url = canonical_url + "?version=pending"
    return html_base(
        title=tag.display_name,
        request=request,
        head_content=opengraph_head(
            title=f"PinDB: {tag.display_name}",
            description=f"Pins tagged {tag.display_name} on PinDB.",
            canonical_url=canonical_url,
            image_url=str(
                request.url_for("get_og_image", entity_type="tag", id=tag.id)
            ),
        ),
        body_content=centered_div(
            content=fragment[
                bread_crumb(
                    entries=[
                        (request.url_for("get_list_index"), "List"),
                        (request.url_for("get_list_tags"), "Tags"),
                        display_name,
                    ]
                ),
                has_pending_chain
                and pending_edit_banner(
                    viewing_pending=viewing_pending,
                    canonical_url=canonical_url,
                    pending_url=pending_url,
                ),
                page_heading(
                    icon="tag",
                    text=display_name,
                    full_width=True,
                    extras=fragment[
                        category_badge(tag.category),
                        user
                        and (user.is_admin or user.is_editor)
                        and icon_button(
                            icon="layers",
                            title="Bulk edit pins with this tag",
                            href=f"/bulk-edit/from/tag/{tag.id}",
                        ),
                        user
                        and (user.is_admin or user.is_editor)
                        and icon_button(
                            icon="pen",
                            title="Edit tag",
                            href=str(request.url_for("get_edit_tag", id=tag.id)),
                        ),
                        user
                        and (user.is_admin or user.is_editor)
                        and icon_button(
                            icon="copy",
                            title="Duplicate tag (prefills a new tag form)",
                            href=str(
                                request.url_for("get_create_tag").include_query_params(
                                    duplicate_from=tag.id
                                )
                            ),
                        ),
                        user
                        and user.is_admin
                        and confirm_modal(
                            trigger=icon_button(
                                icon="trash-2",
                                title="Delete tag",
                                variant="danger",
                            ),
                            message=f'Delete the tag "{tag.display_name}"?',
                            form_action=str(
                                request.url_for(
                                    "post_delete_entity",
                                    entity_type="tag",
                                    id=tag.id,
                                )
                            ),
                        ),
                    ],
                ),
                description_block(tag.description),
                audit_timestamps(
                    created_at=tag.created_at,
                    updated_at=tag.updated_at,
                ),
                tag.aliases
                and linked_items_row(
                    icon="arrow-left-right",
                    label="Also known as",
                    items=[
                        code(
                            class_="bg-darker text-base-text rounded px-1.5 py-0.5 text-sm font-mono"
                        )[a.alias]
                        for a in sorted(tag.aliases, key=lambda a: a.alias)
                    ],
                ),
                tag.implications
                and linked_items_row(
                    icon="arrow-right",
                    label="Child of",
                    items=[
                        tag_relation_items(
                            list(tag.implications), request, tag.id, "implications"
                        )
                    ],
                ),
                tag.implied_by
                and linked_items_row(
                    icon="arrow-left",
                    label="Parent of",
                    items=[
                        tag_relation_items(
                            list(tag.implied_by), request, tag.id, "implied_by"
                        )
                    ],
                ),
                paginated_pin_grid(
                    request=request,
                    pins=pins,
                    total_count=total_count,
                    page=page,
                    page_url=str(tag_url(request=request, tag=tag)),
                    per_page=per_page,
                ),
            ],
            flex=True,
            col=True,
        ),
    )

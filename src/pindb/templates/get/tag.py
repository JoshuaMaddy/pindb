from typing import Sequence

from fastapi import Request
from htpy import Element, div, fragment, i, p, span, code

from pindb.database import User
from pindb.database.pin import Pin
from pindb.database.tag import Tag
from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.confirm_modal import confirm_modal
from pindb.templates.components.description_block import description_block
from pindb.templates.components.icon_button import icon_button
from pindb.templates.components.linked_items_row import linked_items_row
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.paginated_pin_grid import paginated_pin_grid
from pindb.templates.components.pending_edit_banner import pending_edit_banner
from pindb.templates.components.pill_link import pill_link
from pindb.templates.components.tag_branding import (
    CATEGORY_COLORS,
    CATEGORY_HOVER_CLASSES,
    CATEGORY_ICONS,
    category_badge,
)


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
            title=tag.category.value.title(),
        )[
            i(data_lucide=icon_name, class_=f"w-4 h-4 shrink-0 {color}"),
            tag.name,
        ]

    return div(class_="flex flex-col gap-1 mt-1")[
        p(class_="text-xs text-pin-base-300 font-semibold")["Tag parents:"],
        div(class_="flex flex-col gap-1")[
            [
                div(class_="flex items-center flex-wrap gap-1")[
                    _badge(source),
                    span(class_="text-pin-base-300 text-xs")["→"],
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
    display_name = ("(P) " + tag.name) if tag.is_pending else tag.name
    canonical_url = str(request.url_for("get_tag", id=tag.id))
    pending_url = canonical_url + "?version=pending"
    return html_base(
        title=tag.name,
        request=request,
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
                            icon="pen",
                            title="Edit tag",
                            href=str(request.url_for("get_edit_tag", id=tag.id)),
                        ),
                        user
                        and user.is_admin
                        and confirm_modal(
                            trigger=icon_button(
                                icon="trash-2",
                                title="Delete tag",
                                variant="danger",
                            ),
                            message=f'Delete the tag "{tag.name}"?',
                            form_action=str(
                                request.url_for("post_delete_tag", id=tag.id)
                            ),
                        ),
                    ],
                ),
                description_block(tag.description),
                tag.aliases
                and linked_items_row(
                    icon="arrow-left-right",
                    label="Also known as",
                    items=[
                        code(
                            class_="bg-pin-base-700 text-pin-base-text rounded px-1.5 py-0.5 text-sm font-mono"
                        )[a.alias]
                        for a in sorted(tag.aliases, key=lambda a: a.alias)
                    ],
                ),
                tag.implications
                and linked_items_row(
                    icon="arrow-right",
                    label="Child of",
                    items=[
                        pill_link(
                            href=str(request.url_for("get_tag", id=t.id)),
                            text=("(P) " + t.name) if t.is_pending else t.name,
                            icon=CATEGORY_ICONS.get(t.category, "tag"),
                            color_classes=CATEGORY_COLORS.get(
                                t.category, "bg-pin-base-500 text-pin-base-text"
                            ),
                            hover_classes=CATEGORY_HOVER_CLASSES.get(
                                t.category, "hover:border-accent hover:text-accent"
                            ),
                        )
                        for t in sorted(tag.implications, key=lambda t: t.name)
                    ],
                ),
                tag.implied_by
                and linked_items_row(
                    icon="arrow-left",
                    label="Parent of",
                    items=[
                        pill_link(
                            href=str(request.url_for("get_tag", id=t.id)),
                            text=("(P) " + t.name) if t.is_pending else t.name,
                            icon=CATEGORY_ICONS.get(t.category, "tag"),
                            color_classes=CATEGORY_COLORS.get(
                                t.category, "bg-pin-base-500 text-pin-base-text"
                            ),
                            hover_classes=CATEGORY_HOVER_CLASSES.get(
                                t.category, "hover:border-accent hover:text-accent"
                            ),
                        )
                        for t in sorted(tag.implied_by, key=lambda t: t.name)
                    ],
                ),
                paginated_pin_grid(
                    request=request,
                    pins=pins,
                    total_count=total_count,
                    page=page,
                    page_url=str(request.url_for("get_tag", id=tag.id)),
                    per_page=per_page,
                ),
            ],
            flex=True,
            col=True,
        ),
    )

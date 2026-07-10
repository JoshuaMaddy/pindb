"""Shared per-variant rendering for message bodies, plus the click-target resolver.

Messages carry no title/image columns — the visible title and leading visual are
derived from the typed ``body`` variant here, so the inbox page and the navbar
preview render identically.
"""

from __future__ import annotations

from fastapi import Request
from htpy import Element, Node, i, span

from pindb.achievements import AchievementFamily
from pindb.database.entity_type import EntityType
from pindb.database.message import Message
from pindb.markdown_utils import render_md
from pindb.models.message_body import (
    AchievementBody,
    ContributionBody,
    MessageBody,
    PinRejectionBody,
    TextBody,
)
from pindb.templates.components.achievements.badge import achievement_badge

# EntityType -> the named GET route for that entity's detail page. The slug path
# param is decorative (handlers canonical-redirect on mismatch), so a placeholder
# slug is safe.
_ENTITY_ROUTE: dict[EntityType, str] = {
    EntityType.pin: "get_pin",
    EntityType.shop: "get_shop",
    EntityType.artist: "get_artist",
    EntityType.tag: "get_tag",
    EntityType.pin_set: "get_pin_set",
}

# Non-achievement variants get a plain Lucide glyph.
_ICON_NAMES: dict[type, str] = {
    TextBody: "mail",
    PinRejectionBody: "circle-x",
    ContributionBody: "sparkles",
}


def message_title(body: MessageBody) -> str:
    """Human-readable title derived from the body variant."""
    if isinstance(body, AchievementBody):
        return f"Achievement unlocked: {body.name}"
    if isinstance(body, PinRejectionBody):
        return "Pin submission rejected"
    if isinstance(body, ContributionBody):
        return "Contribution recorded"
    if isinstance(body, TextBody):
        first_line = next(
            (line.strip() for line in body.text.splitlines() if line.strip()),
            "",
        )
        return first_line or "Message"
    return "Message"


def message_visual(body: MessageBody) -> Element:
    """Leading visual: the achievement badge, else a category Lucide icon."""
    if isinstance(body, AchievementBody):
        return achievement_badge(
            family=AchievementFamily(body.family),
            tier=body.tier,
        )
    icon_name = _ICON_NAMES.get(type(body), "mail")
    return span(
        class_="inline-flex items-center justify-center text-lightest-hover shrink-0"
    )[i(data_lucide=icon_name, class_="w-5 h-5", aria_hidden="true")]


def render_message_body(body: MessageBody) -> Node:
    """The message's detail text, rendered safely."""
    if isinstance(body, AchievementBody):
        return span(class_="text-lightest-hover")[
            f"{body.threshold}+ {body.unit_label}"
        ]
    if isinstance(body, PinRejectionBody):
        return render_md(body.reason)
    if isinstance(body, ContributionBody):
        suffix = f" (+{body.points})" if body.points is not None else ""
        return span[f"{body.summary}{suffix}"]
    if isinstance(body, TextBody):
        return render_md(body.text)
    return None


def message_target_url(request: Request, message: Message) -> str | None:
    """Resolve a click-through URL: explicit ``redirect_url`` > related entity > None."""
    if message.body.redirect_url:
        return message.body.redirect_url
    entity_type = message.related_entity_type
    entity_id = message.related_entity_id
    if entity_type is None or entity_id is None:
        return None
    return str(
        request.url_for(
            _ENTITY_ROUTE[entity_type],
            slug=entity_type.slug,
            id=entity_id,
        )
    )

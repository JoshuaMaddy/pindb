"""htpy fragment builders: achievement badge chips for user profiles.

Modeled on ``tag_branding.category_badge``. Class strings live in dicts of
full literals so the Tailwind scanner sees every generated utility; the
``badge-family-*`` / ``badge-metal-*`` component classes (``input.css``) set
the CSS variables the gradient metal border reads.
"""

from __future__ import annotations

from htpy import Element, div, i, span

from pindb.achievements import (
    FAMILY_SPECS,
    TIER_METALS,
    TIER_NUMERALS,
    AchievementFamily,
    FamilySpec,
    tier_tooltip,
)

ACHIEVEMENT_FAMILY_CLASSES: dict[AchievementFamily, str] = {
    AchievementFamily.pinsmith: "badge-family-pinsmith text-achievement-pinsmith-fg",
    AchievementFamily.polisher: "badge-family-polisher text-achievement-polisher-fg",
    AchievementFamily.taxonomist: "badge-family-taxonomist text-achievement-taxonomist-fg",
    AchievementFamily.archivist: "badge-family-archivist text-achievement-archivist-fg",
    AchievementFamily.merchant: "badge-family-merchant text-achievement-merchant-fg",
    AchievementFamily.appraiser: "badge-family-appraiser text-achievement-appraiser-fg",
    AchievementFamily.patron: "badge-family-patron text-achievement-patron-fg",
    AchievementFamily.restorer: "badge-family-restorer text-achievement-restorer-fg",
    AchievementFamily.curator: "badge-family-curator text-achievement-curator-fg",
    AchievementFamily.pin_lover: "badge-family-pin-lover text-achievement-pin-lover-fg",
    AchievementFamily.hoarder: "badge-family-hoarder text-achievement-hoarder-fg",
    AchievementFamily.hunter: "badge-family-hunter text-achievement-hunter-fg",
}

# stroke-* alongside text-*: the base `* { color: base-text }` rule targets the
# lucide-generated svg paths directly, so currentColor inheritance alone loses
# (same reason CATEGORY_COLORS carries stroke-tag-*-fg).
ACHIEVEMENT_FG_CLASSES: dict[AchievementFamily, str] = {
    AchievementFamily.pinsmith: "text-achievement-pinsmith-fg stroke-achievement-pinsmith-fg",
    AchievementFamily.polisher: "text-achievement-polisher-fg stroke-achievement-polisher-fg",
    AchievementFamily.taxonomist: "text-achievement-taxonomist-fg stroke-achievement-taxonomist-fg",
    AchievementFamily.archivist: "text-achievement-archivist-fg stroke-achievement-archivist-fg",
    AchievementFamily.merchant: "text-achievement-merchant-fg stroke-achievement-merchant-fg",
    AchievementFamily.appraiser: "text-achievement-appraiser-fg stroke-achievement-appraiser-fg",
    AchievementFamily.patron: "text-achievement-patron-fg stroke-achievement-patron-fg",
    AchievementFamily.restorer: "text-achievement-restorer-fg stroke-achievement-restorer-fg",
    AchievementFamily.curator: "text-achievement-curator-fg stroke-achievement-curator-fg",
    AchievementFamily.pin_lover: "text-achievement-pin-lover-fg stroke-achievement-pin-lover-fg",
    AchievementFamily.hoarder: "text-achievement-hoarder-fg stroke-achievement-hoarder-fg",
    AchievementFamily.hunter: "text-achievement-hunter-fg stroke-achievement-hunter-fg",
}

METAL_BORDER_CLASSES: dict[str, str] = {
    "bronze": "badge-metal-bronze",
    "silver": "badge-metal-silver",
    "gold": "badge-metal-gold",
    "platinum": "badge-metal-platinum",
}


def achievement_badge(
    family: AchievementFamily,
    tier: int,
) -> Element:
    """Chip for one earned achievement tier (icon + roman numeral).

    Single-tier families (Pin Lover) render with the gold border and no
    numeral. The badge name + threshold serve as the hover tooltip.
    """
    spec: FamilySpec = FAMILY_SPECS[family]
    multi_tier: bool = len(spec.thresholds) > 1
    metal: str = TIER_METALS[tier - 1] if multi_tier else "gold"
    tooltip: str = tier_tooltip(spec=spec, tier=tier)
    foreground: str = ACHIEVEMENT_FG_CLASSES[family]

    return span(
        class_=(
            "achievement-badge inline-flex items-center gap-1 p-1.5 rounded "
            f"text-xs font-semibold {ACHIEVEMENT_FAMILY_CLASSES[family]} "
            f"{METAL_BORDER_CLASSES[metal]}"
        ),
        title=tooltip,
        aria_label=tooltip,
        role="img",
    )[
        i(
            data_lucide=spec.icon,
            class_=f"w-4 h-4 shrink-0 {foreground}",
            aria_hidden="true",
        ),
        multi_tier and span(class_=foreground)[TIER_NUMERALS[tier - 1]],
    ]


def achievement_badge_row(highest_tiers: dict[str, int]) -> Element | None:
    """Row of the highest earned tier per family, in registry order.

    Args:
        highest_tiers: ``family value -> max earned tier`` (from
            ``user_achievements``).

    Returns:
        Element | None: The badge row, or ``None`` when nothing is earned
        (htpy drops falsy children).
    """
    badges: list[Element] = [
        achievement_badge(family=family, tier=highest_tiers[family.value])
        for family in FAMILY_SPECS
        if family.value in highest_tiers
    ]
    if not badges:
        return None
    return div(
        class_="flex flex-wrap gap-2",
        aria_label="Achievements",
    )[badges]

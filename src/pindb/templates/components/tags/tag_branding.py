"""
htpy page and fragment builders: `templates/components/tags/tag_branding.py`.
"""

from htpy import Element, i, span
from titlecase import titlecase

from pindb.database.tag import TagCategory

CATEGORY_COLORS: dict[TagCategory, str] = {
    TagCategory.general: "bg-tag-general text-tag-general-fg fill-tag-general-fg stroke-tag-general-fg border-tag-general-fg",
    TagCategory.copyright: "bg-tag-copyright text-tag-copyright-fg stroke-tag-copyright-fg border-tag-copyright-fg",
    TagCategory.character: "bg-tag-character text-tag-character-fg fill-tag-character-fg stroke-tag-character-fg border-tag-character-fg",
    TagCategory.archetype: "bg-tag-archetype text-tag-archetype-fg stroke-tag-archetype-fg border-tag-archetype-fg",
    TagCategory.species: "bg-tag-species text-tag-species-fg fill-tag-species-fg stroke-tag-species-fg border-tag-species-fg",
    TagCategory.company: "bg-tag-company text-tag-company-fg stroke-tag-company-fg border-tag-company-fg",
    TagCategory.meta: "bg-tag-meta text-tag-meta-fg stroke-tag-meta-fg border-tag-meta-fg",
    TagCategory.material: "bg-tag-material text-tag-material-fg fill-tag-material-fg stroke-tag-material-fg border-tag-material-fg",
    TagCategory.color: "bg-tag-color text-tag-color-fg fill-tag-color-fg stroke-tag-color-fg border-tag-color-fg",
}

CATEGORY_ICONS: dict[TagCategory, str] = {
    TagCategory.general: "tag",
    TagCategory.copyright: "copyright",
    TagCategory.character: "user",
    TagCategory.archetype: "book-user",
    TagCategory.species: "paw-print",
    TagCategory.company: "building-2",
    TagCategory.meta: "info",
    TagCategory.material: "gem",
    TagCategory.color: "paint-bucket",
}

CATEGORY_HOVER_CLASSES: dict[TagCategory, str] = {
    TagCategory.general: "hover:border-tag-general-hover hover:text-tag-general-hover hover:fill-tag-general-hover hover:stroke-tag-general-hover hover:border-tag-general-hover",
    TagCategory.copyright: "hover:border-tag-copyright-hover hover:text-tag-copyright-hover hover:stroke-tag-copyright-hover hover:border-tag-copyright-hover",
    TagCategory.character: "hover:border-tag-character-hover hover:text-tag-character-hover hover:fill-tag-character-hover hover:stroke-tag-character-hover hover:border-tag-character-hover",
    TagCategory.archetype: "hover:border-tag-archetype-hover hover:text-tag-archetype-hover hover:stroke-tag-archetype-hover hover:border-tag-archetype-hover",
    TagCategory.species: "hover:border-tag-species-hover hover:text-tag-species-hover hover:fill-tag-species-hover hover:stroke-tag-species-hover hover:border-tag-species-hover",
    TagCategory.company: "hover:border-tag-company-hover hover:text-tag-company-hover hover:stroke-tag-company-hover hover:border-tag-company-hover",
    TagCategory.meta: "hover:border-tag-meta-hover hover:text-tag-meta-hover hover:stroke-tag-meta-hover hover:border-tag-meta-hover",
    TagCategory.material: "hover:border-tag-material-hover hover:text-tag-material-hover hover:fill-tag-material-hover hover:stroke-tag-material-hover hover:border-tag-material-hover",
    TagCategory.color: "hover:border-tag-color-hover hover:text-tag-color-hover hover:fill-tag-color-hover hover:stroke-tag-color-hover hover:border-tag-color-hover",
}


def category_badge(category: TagCategory, additional_classes: str = "") -> Element:
    color = CATEGORY_COLORS.get(category, "bg-tag-general text-tag-general-fg")
    icon_name = CATEGORY_ICONS.get(category, "tag")
    label = titlecase(category.value)
    return span(
        class_=f"p-1.5 rounded text-xs font-medium border {color} {additional_classes}",
        title=label,
        aria_label=label,
        role="img",
    )[i(data_lucide=icon_name, class_=f"w-4 h-4 {color}", aria_hidden="true"),]

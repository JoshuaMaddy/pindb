"""Render user-authored Markdown to sanitized HTML for safe insertion into pages.

Uses ``markdown-it-py`` for parsing and ``nh3`` for allowlisting tags and
attributes so scripts and unsafe URLs cannot be injected.
"""

import nh3
from markdown_it import MarkdownIt
from markupsafe import Markup

_md = MarkdownIt()

_ALLOWED_TAGS: frozenset[str] = frozenset(
    {"p", "br", "strong", "em", "a", "ul", "ol", "li", "blockquote", "del"}
)

_ALLOWED_ATTRS: dict[str, set[str]] = {
    "a": {"href", "title"},
}

_ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https", "mailto"})


def render_md(text: str | None) -> Markup | None:
    """Render Markdown to sanitized HTML suitable for ``Markup`` insertion.

    Args:
        text (str | None): Raw Markdown, or ``None`` / empty for absent content.

    Returns:
        Markup | None: Sanitized HTML, or ``None`` when *text* is falsy or the
            result is whitespace-only after cleaning.
    """
    if not text:
        return None
    raw_html = _md.render(text)
    clean_html = nh3.clean(
        raw_html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        url_schemes=_ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer",
    )
    return Markup(clean_html) if clean_html.strip() else None

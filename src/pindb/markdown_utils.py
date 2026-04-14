from markdown_it import MarkdownIt
from markupsafe import Markup

import nh3

_md = MarkdownIt()

_ALLOWED_TAGS: frozenset[str] = frozenset(
    {"p", "br", "strong", "em", "a", "ul", "ol", "li", "blockquote", "del"}
)

_ALLOWED_ATTRS: dict[str, set[str]] = {
    "a": {"href", "title"},
}

_ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https", "mailto"})


def render_md(text: str | None) -> Markup | None:
    """Render markdown to sanitized HTML. Returns None for empty/None input."""
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

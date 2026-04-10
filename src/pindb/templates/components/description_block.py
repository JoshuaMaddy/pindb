from htpy import Fragment, div, fragment, p


def description_block(text: str | None) -> Fragment:
    """Renders a paragraph block when text is non-empty; renders nothing otherwise."""
    return fragment[bool(text) and div[p[text]]]

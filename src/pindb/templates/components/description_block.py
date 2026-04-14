from htpy import Fragment, div, fragment

from pindb.markdown_utils import render_md


def description_block(text: str | None) -> Fragment:
    """Render a markdown description block. No-op when text is empty."""
    html = render_md(text)
    return fragment[bool(html) and div(class_="markdown-content")[html]]

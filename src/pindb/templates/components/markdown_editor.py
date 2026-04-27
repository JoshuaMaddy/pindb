"""
htpy page and fragment builders: `templates/components/markdown_editor.py`.
"""

from htpy import Element, div, input, span


def markdown_editor(
    field_id: str,
    name: str,
    value: str | None = None,
) -> Element:
    """
    Overtype markdown editor with live preview panel.

    Renders a hidden input (submitted with the form) synced to an Overtype
    editor instance. Preview updates live via marked.js.

    Layout: stacked on small screens, side-by-side on md+.
    """
    editor_el_id = f"md-editor-{field_id}"
    preview_el_id = f"{field_id}-preview"

    return div(class_="flex flex-col md:flex-row gap-4")[
        # ── Editor column ────────────────────────────────────────────────────
        div(class_="flex-1 flex flex-col gap-1")[
            span(
                class_="text-xs font-medium uppercase tracking-wide text-lightest-hover"
            )["Write"],
            div(
                id=editor_el_id,
                class_="overtype-wrapper",
                data_md_editor=field_id,
            ),
            # Hidden input submitted with the form; overtype syncs via onChange
            input(
                type="hidden",
                id=field_id,
                name=name,
                value=value or "",
            ),
        ],
        # ── Preview column ───────────────────────────────────────────────────
        div(class_="flex-1 flex flex-col gap-1")[
            span(
                class_="text-xs font-medium uppercase tracking-wide text-lightest-hover"
            )["Preview"],
            div(
                id=preview_el_id,
                class_="markdown-content min-h-20 p-3 rounded-lg bg-main border border-lightest",
            ),
        ],
    ]

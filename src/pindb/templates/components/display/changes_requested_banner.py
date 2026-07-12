"""
htpy page and fragment builders: `templates/components/display/changes_requested_banner.py`.
"""

from htpy import Element, a, div, i

from pindb.markdown_utils import render_md

_BANNER_CLASS: str = (
    "rounded bg-pending-dark border border-pending-dark text-pending-main "
    "px-4 py-2 text-sm my-2 flex flex-col gap-1"
)


def changes_requested_banner(
    *,
    reason: str | None,
    edit_url: str | None = None,
    is_edit: bool = False,
) -> Element:
    """Shown on an entry a reviewer sent back, above the entry itself.

    Only editors and admins can see a needs-changes entry at all (the ORM query
    filter hides it from everyone else), and the pending-edit view is already
    editor-gated, so this needs no role gate of its own. The reason is rendered as
    markdown — the same text the submitter got in their inbox.

    ``is_edit`` distinguishes a flagged *proposed edit* to an approved entry from a
    flagged *submission*: the entity row is untouched by an edit rejection, so the
    copy has to say which of the two the reviewer sent back.
    """
    headline = (
        "A reviewer asked for changes to the proposed edit."
        if is_edit
        else "A reviewer asked for changes before this can be approved."
    )
    return div(class_=_BANNER_CLASS)[
        div(class_="flex items-center gap-2")[
            i(
                data_lucide="message-square-warning",
                class_="inline-block w-4 h-4 shrink-0",
                aria_hidden="true",
            ),
            div(class_="text-pending-main font-medium")[headline],
            edit_url
            and a(
                href=edit_url,
                class_="underline text-pending-main-hover hover:text-pending-main ml-auto shrink-0",
            )["Edit to resubmit →"],
        ],
        reason
        and div(class_="text-lightest-hover text-sm max-w-none")[render_md(reason)],
    ]

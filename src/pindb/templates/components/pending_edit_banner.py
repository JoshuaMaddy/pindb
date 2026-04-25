"""
htpy page and fragment builders: `templates/components/pending_edit_banner.py`.
"""

from htpy import Element, a, div, i


def pending_edit_banner(
    *,
    viewing_pending: bool,
    canonical_url: str,
    pending_url: str,
) -> Element:
    """Banner shown to editors/admins on canonical or pending entity views."""
    if viewing_pending:
        return div(
            class_="rounded bg-amber-900 border border-amber-600 text-amber-200 px-4 py-2 text-sm my-2 flex items-center gap-2"
        )[
            i(data_lucide="clock", class_="inline-block w-4 h-4", aria_hidden="true"),
            "Viewing pending edit.",
            a(
                href=canonical_url,
                class_="underline text-amber-100 hover:text-white ml-auto",
            )["View canonical →"],
        ]
    return div(
        class_="rounded bg-amber-900 border border-amber-600 text-amber-200 px-4 py-2 text-sm my-2 flex items-center gap-2"
    )[
        i(data_lucide="clock", class_="inline-block w-4 h-4", aria_hidden="true"),
        "This entry has a pending edit awaiting approval.",
        a(
            href=pending_url,
            class_="underline text-amber-100 hover:text-white ml-auto",
        )["View pending →"],
    ]

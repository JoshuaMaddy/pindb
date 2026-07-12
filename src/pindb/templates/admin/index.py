"""
htpy page and fragment builders: `templates/admin/index.py`.
"""

from fastapi import Request
from htpy import Element, a, button, div, form, hr, i, p, span

from pindb.templates.base import html_base
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading


def admin_panel_page(
    request: Request, pending_count: int = 0, report_count: int = 0
) -> Element:
    return html_base(
        title="Admin Panel",
        request=request,
        body_content=centered_div(
            content=[
                page_heading(
                    icon="shield",
                    text="Admin Panel",
                ),
                hr,
                _pending_section(request, pending_count),
                hr,
                _reports_section(request, report_count),
                hr,
                _users_section(request),
                hr,
                _tags_bulk_section(request),
                hr,
                _search_section(),
                hr,
                _stats_section(),
            ],
            flex=True,
            col=True,
        ),
    )


def _pending_section(request: Request, pending_count: int) -> Element:
    badge: Element | str = (
        span(
            class_="text-xs font-semibold px-2 py-0.5 rounded bg-pending-dark-hover text-pending-main-hover"
        )[str(pending_count)]
        if pending_count > 0
        else span(class_="text-xs font-semibold px-2 py-0.5 rounded")["0"]
    )
    return div(class_="flex flex-col gap-2")[
        div(class_="flex items-baseline gap-2")[
            page_heading(icon="clock", text="Pending Approvals", level=2),
            badge,
        ],
        p(class_="text-sm")[
            "Review entries submitted by editors that are awaiting admin approval."
        ],
        a(
            href="/admin/pending",
            class_="btn btn-primary w-fit",
        )[
            i(
                data_lucide="clock",
                class_="inline-block w-4 h-4 mr-1",
                aria_hidden="true",
            ),
            "Review Pending",
        ],
    ]


def _reports_section(request: Request, report_count: int) -> Element:
    badge: Element = (
        span(
            class_="text-xs font-semibold px-2 py-0.5 rounded bg-error-dark-hover text-error-main-hover"
        )[str(report_count)]
        if report_count > 0
        else span(class_="text-xs font-semibold px-2 py-0.5 rounded")["0"]
    )
    return div(class_="flex flex-col gap-2")[
        div(class_="flex items-baseline gap-2")[
            page_heading(icon="flag", text="Reports", level=2),
            badge,
        ],
        p(class_="text-sm")[
            "Review content users have flagged — dismiss the report or take the "
            "content down."
        ],
        a(
            href=str(request.url_for("get_admin_reports")),
            class_="btn btn-primary w-fit",
        )[
            i(
                data_lucide="flag",
                class_="inline-block w-4 h-4 mr-1",
                aria_hidden="true",
            ),
            "Review Reports",
        ],
    ]


def _users_section(request: Request) -> Element:
    return div(class_="flex flex-col gap-2")[
        page_heading(
            icon="users",
            text="User Management",
            level=2,
        ),
        p(class_="text-sm")["Promote or demote users to/from admin."],
        a(
            href=str(request.url_for("get_admin_users")),
            class_="btn btn-primary w-fit",
        )[
            i(
                data_lucide="user-cog",
                class_="inline-block w-4 h-4 mr-1",
                aria_hidden="true",
            ),
            "Manage Users",
        ],
    ]


def _tags_bulk_section(request: Request) -> Element:
    return div(class_="flex flex-col gap-2")[
        page_heading(
            icon="tags",
            text="Bulk tags",
            level=2,
        ),
        p(class_="text-sm")[
            "Paste or upload JSON to merge or create tag trees (aliases and implications)."
        ],
        a(
            href=str(request.url_for("get_admin_bulk_tags")),
            class_="btn btn-primary w-fit",
        )[
            i(
                data_lucide="tags",
                class_="inline-block w-4 h-4 mr-1",
                aria_hidden="true",
            ),
            "Bulk tags…",
        ],
    ]


def _trigger_form(action: str, icon: str, label: str) -> Element:
    """Fire-and-forget POST button for a background job (no-JS fallback intact)."""
    return form(
        method="post",
        action=action,
        hx_post=action,
        hx_swap="none",
        **{"data-htmx-submit-guard": ""},
    )[
        button(
            type="submit",
            class_="btn btn-primary",
        )[
            i(
                data_lucide=icon,
                class_="inline-block w-4 h-4 mr-1",
                aria_hidden="true",
            ),
            label,
        ]
    ]


def _search_section() -> Element:
    return div(class_="flex flex-col gap-2")[
        page_heading(
            icon="search",
            text="Search Index",
            level=2,
        ),
        p(class_="text-sm")[
            "Synchronize the Meilisearch index with the current database state. "
            "This re-indexes all pins and removes stale entries."
        ],
        _trigger_form(
            action="/admin/search/sync",
            icon="refresh-cw",
            label="Sync Search Index",
        ),
    ]


def _stats_section() -> Element:
    return div(class_="flex flex-col gap-2")[
        page_heading(
            icon="trophy",
            text="Stats & Achievements",
            level=2,
        ),
        p(class_="text-sm")[
            "Recompute every user's contribution stats from source and award any "
            "achievements they have earned. Routes keep these fresh already; this "
            "heals a missed refresh without waiting for the hourly sweep."
        ],
        _trigger_form(
            action="/admin/stats/refresh",
            icon="refresh-cw",
            label="Refresh User Stats",
        ),
    ]

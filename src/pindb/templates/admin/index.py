from fastapi import Request
from htpy import Element, a, button, div, form, hr, i, p

from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.page_heading import page_heading


def admin_panel_page(request: Request) -> Element:
    return html_base(
        title="Admin Panel",
        request=request,
        body_content=centered_div(
            content=[
                page_heading(
                    icon="shield",
                    text="Admin Panel",
                    gap=3,
                ),
                hr,
                _users_section(request),
                hr,
                _search_section(),
            ],
            flex=True,
            col=True,
        ),
    )


def _users_section(request: Request) -> Element:
    return div(class_="flex flex-col gap-3")[
        page_heading(
            icon="users",
            text="User Management",
            level=2,
        ),
        p(class_="text-pin-base-300 text-sm")["Promote or demote users to/from admin."],
        a(
            href=str(request.url_for("get_admin_users")),
            class_="btn btn-primary w-fit",
        )[
            i(data_lucide="user-cog", class_="inline-block w-4 h-4 mr-1"),
            "Manage Users",
        ],
    ]


def _search_section() -> Element:
    return div(class_="flex flex-col gap-3")[
        page_heading(
            icon="search",
            text="Search Index",
            level=2,
        ),
        p(class_="text-pin-base-300 text-sm")[
            "Synchronize the Meilisearch index with the current database state. "
            "This re-indexes all pins and removes stale entries."
        ],
        form(
            method="post",
            action="/admin/search/sync",
            hx_post="/admin/search/sync",
            hx_swap="none",
        )[
            button(
                type_="submit",
                class_="btn btn-primary",
            )[
                i(data_lucide="refresh-cw", class_="inline-block w-4 h-4 mr-1"),
                "Sync Search Index",
            ]
        ],
    ]

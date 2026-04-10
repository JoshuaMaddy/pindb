from typing import Sequence

from fastapi import Request
from htpy import Element, button, div, form, h1, hr, i, span, td, tr

from pindb.database.user import User
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.data_table import TableColumn, data_table


def admin_users_page(
    request: Request,
    users: Sequence[User],
    current_user_id: int,
) -> Element:
    rows: list[dict[str, int | str]] = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email or "",
            "is_admin": user.is_admin,
            "promote_url": str(request.url_for("promote_user", user_id=user.id)),
            "demote_url": str(request.url_for("demote_user", user_id=user.id)),
        }
        for user in users
    ]

    columns = [
        TableColumn("Username", key="username"),
        TableColumn("Email", key="email"),
        TableColumn("Role", key="is_admin"),
        TableColumn("Actions", sortable=False),
    ]

    return html_base(
        title="Manage Users",
        request=request,
        body_content=centered_div(
            content=[
                div(class_="flex items-baseline gap-3")[
                    i(data_lucide="users", class_="inline-block"),
                    h1["Manage Users"],
                ],
                hr,
                data_table(
                    table_id="users",
                    columns=columns,
                    rows=rows,
                    row_template=_user_row_template(),
                    search_keys=["username", "email"],
                    page_size=25,
                    default_sort_col="username",
                    extra_state={"currentUserId": current_user_id},
                ),
            ],
            flex=True,
            col=True,
        ),
    )


def _user_row_template() -> Element:
    """Alpine-bound <tr> — 'row' is provided by x-for in the data_table component."""
    is_self = "row.is_admin && row.id === currentUserId"
    action_url = "row.is_admin ? row.demote_url : row.promote_url"
    btn_class = (
        f"{is_self} ? 'btn btn-sm opacity-50 cursor-not-allowed'"
        " : row.is_admin ? 'btn btn-sm btn-error'"
        " : 'btn btn-sm btn-primary'"
    )
    btn_text = (
        f"{is_self} ? 'Cannot demote self'"
        " : row.is_admin ? 'Demote'"
        " : 'Promote to Admin'"
    )

    return tr(class_="border-b border-pin-base-800")[
        td(class_="py-2 pr-6", **{"x-text": "row.username"}),
        td(
            class_="py-2 pr-6 text-pin-base-400",
            **{"x-text": "row.email || '—'"},
        ),
        td(class_="py-2 pr-6")[
            span(
                class_="text-xs font-semibold px-2 py-0.5 rounded",
                **{
                    ":class": (
                        "row.is_admin"
                        " ? 'bg-amber-700 text-amber-100'"
                        " : 'bg-pin-base-700 text-pin-base-300'"
                    ),
                    "x-text": "row.is_admin ? 'Admin' : 'User'",
                },
            ),
        ],
        td(class_="py-2")[
            form(method="post", **{":action": action_url})[
                button(
                    type_="submit",
                    **{
                        ":class": btn_class,
                        ":disabled": is_self,
                        "x-text": btn_text,
                    },
                ),
            ]
        ],
    ]

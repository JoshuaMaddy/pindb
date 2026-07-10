"""
htpy page and fragment builders: `templates/admin/users.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element, div, h1, hr, i

from pindb.database.user import User
from pindb.templates.base import html_base
from pindb.templates.components.islands import island
from pindb.templates.components.layout.centered import centered_div


def admin_users_page(
    request: Request,
    users: Sequence[User],
    current_user_id: int,
) -> Element:
    rows: list[dict[str, int | str | bool]] = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email or "",
            "is_admin": user.is_admin,
            "is_editor": user.is_editor,
            "promote_url": str(request.url_for("promote_user", user_id=user.id)),
            "demote_url": str(request.url_for("demote_user", user_id=user.id)),
            "promote_editor_url": str(
                request.url_for("promote_editor", user_id=user.id)
            ),
            "demote_editor_url": str(request.url_for("demote_editor", user_id=user.id)),
            "delete_account_url": str(
                request.url_for("delete_account", user_id=user.id)
            ),
        }
        for user in users
    ]

    return html_base(
        title="Manage Users",
        request=request,
        body_content=centered_div(
            content=[
                div(class_="flex items-baseline gap-2")[
                    i(data_lucide="users", class_="inline-block"),
                    h1["Manage Users"],
                ],
                hr,
                island(
                    "admin-users",
                    props={
                        "rows": rows,
                        "currentUserId": current_user_id,
                        "pageSize": 25,
                    },
                ),
            ],
            flex=True,
            col=True,
        ),
    )

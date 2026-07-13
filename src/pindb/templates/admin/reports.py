"""Admin content-report queue.

Renders defensively when a report's target has already gone away — the owner may
have removed the photo, or their account may have been erased, and neither is an
error worth 500ing over.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from htpy import Element, button, div, form, p, span

from pindb.database.content_report import ContentReport
from pindb.database.user_display import UserDisplayImage
from pindb.templates.base import html_base
from pindb.templates.components.display.empty_state import empty_state
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading
from pindb.templates.components.pins.pin_thumbnail import pin_thumbnail_img

_REPORTS_ID: str = "admin-reports-content"


@dataclass(frozen=True)
class ReportRow:
    """One open report plus its target, when the target still exists."""

    report: ContentReport
    image: UserDisplayImage | None
    owner_username: str | None


def _action_form(*, action: str, label: str, danger: bool = False) -> Element:
    classes = (
        "btn btn-danger" if danger else "btn btn-primary"
    ) + " cursor-pointer text-sm"
    return form(
        method="post",
        action=action,
        hx_post=action,
        hx_target=f"#{_REPORTS_ID}",
        hx_swap="outerHTML",
        **{"data-htmx-submit-guard": ""},
    )[button(type="submit", class_=classes)[label]]


def _target_preview(*, request: Request, row: ReportRow) -> Element:
    if row.image is None:
        return p(class_="text-sm text-lightest-hover italic")[
            "The reported content no longer exists."
        ]
    caption = row.image.caption or "(no caption)"
    return div(class_="flex items-start gap-3")[
        pin_thumbnail_img(
            request,
            row.image.image_guid,
            sizes="96px",
            alt="Reported display photo",
            class_="h-24 w-24 rounded object-cover",
        ),
        div(class_="flex flex-col gap-1 min-w-0")[
            p(class_="text-sm")[
                "Display photo by ",
                span(class_="font-medium")[row.owner_username or "an erased account"],
            ],
            p(class_="text-sm text-lightest-hover wrap-break-word")[caption],
            row.image.deleted_at
            and p(class_="text-xs text-error-main")["Already removed."],
        ],
    ]


def _report_card(*, request: Request, row: ReportRow) -> Element:
    report = row.report
    reporter = report.reporter.username if report.reporter else "an erased account"
    return div(class_="flex flex-col gap-3 rounded-lg border border-lightest p-4")[
        _target_preview(request=request, row=row),
        div(class_="flex flex-col gap-1")[
            p(class_="text-xs text-lightest-hover")[
                f"Reported by {reporter} on {report.created_at:%Y-%m-%d %H:%M} UTC"
            ],
            p(class_="wrap-break-word")[report.reason],
        ],
        div(class_="flex flex-wrap gap-2")[
            _action_form(
                action=str(request.url_for("post_dismiss_report", report_id=report.id)),
                label="Dismiss",
            ),
            _action_form(
                action=str(
                    request.url_for("post_report_delete_content", report_id=report.id)
                ),
                label="Remove content",
                danger=True,
            ),
        ],
    ]


def _reports_content(*, request: Request, rows: list[ReportRow]) -> Element:
    return div(id=_REPORTS_ID, class_="flex flex-col gap-4")[
        [_report_card(request=request, row=row) for row in rows]
        if rows
        else empty_state("No open reports.")
    ]


def admin_reports_page(
    *,
    request: Request,
    rows: list[ReportRow],
    fragment: bool = False,
) -> Element:
    content = _reports_content(request=request, rows=rows)
    if fragment:
        return content

    return html_base(
        title="Reports",
        request=request,
        body_content=centered_div(
            content=[
                page_heading(
                    icon="flag",
                    text=f"Open Reports ({len(rows)})",
                    heading_id="admin-reports-heading",
                ),
                content,
            ],
            flex=True,
            col=True,
        ),
    )

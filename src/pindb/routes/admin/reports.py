"""Admin queue for user-filed content reports.

Auth comes from the parent router (``routes/admin/__init__.py`` mounts this under
``dependencies=[Depends(require_admin)]``), so no per-route dependency here.

Two things this module has to get right, both consequences of ``ContentReport``
carrying a polymorphic ``(target_type, target_id)`` pointer with no foreign key:

1. Acting on a report must also close **every other open report on the same
   target** — otherwise the queue keeps surfacing reports against content that is
   already gone.
2. The queue has to render when a target has vanished by some other path (account
   erasure, the owner deleting the photo). A missing target is a normal state, not
   a 500.
"""

from typing import Sequence

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pindb.database import async_session_maker
from pindb.database.content_report import (
    ContentReport,
    ReportStatus,
    ReportTargetType,
)
from pindb.database.user import User
from pindb.database.user_display import UserDisplay, UserDisplayImage
from pindb.templates.admin.reports import ReportRow, admin_reports_page
from pindb.utils import utc_now

router = APIRouter(prefix="/reports")


async def _load_open_reports(session: AsyncSession) -> list[ReportRow]:
    """Open reports, newest first, each paired with its target if it still exists."""
    reports: Sequence[ContentReport] = (
        await session.scalars(
            select(ContentReport)
            .where(ContentReport.status == ReportStatus.open)
            .order_by(ContentReport.created_at.desc())
            .options(selectinload(ContentReport.reporter))
        )
    ).all()

    image_ids = [
        report.target_id
        for report in reports
        if report.target_type is ReportTargetType.display_image
    ]
    images: dict[int, UserDisplayImage] = {}
    owners: dict[int, str] = {}
    if image_ids:
        rows = (
            await session.execute(
                select(UserDisplayImage, User.username)
                .join(UserDisplay, UserDisplay.id == UserDisplayImage.display_id)
                .join(User, User.id == UserDisplay.user_id)
                .where(UserDisplayImage.id.in_(image_ids))
                # The owner may have soft-deleted the photo since it was reported;
                # an admin still needs to see what was flagged.
                .execution_options(include_deleted=True)
            )
        ).all()
        for image, username in rows:
            images[image.id] = image
            owners[image.id] = username

    return [
        ReportRow(
            report=report,
            image=images.get(report.target_id),
            owner_username=owners.get(report.target_id),
        )
        for report in reports
    ]


@router.get("", response_model=None, name="get_admin_reports")
async def get_admin_reports(request: Request) -> HTMLResponse:
    async with async_session_maker() as db:
        rows = await _load_open_reports(db)
        return HTMLResponse(content=str(admin_reports_page(request=request, rows=rows)))


async def _resolve(
    session: AsyncSession,
    report: ContentReport,
    *,
    status: ReportStatus,
    admin_id: int,
) -> None:
    report.status = status
    report.resolved_at = utc_now()
    report.resolved_by_id = admin_id


@router.post("/{report_id}/dismiss", response_model=None, name="post_dismiss_report")
async def post_dismiss_report(
    request: Request,
    report_id: int,
) -> HTMLResponse:
    admin: User = request.state.user
    async with async_session_maker.begin() as db:
        report = await db.get(ContentReport, report_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")
        await _resolve(db, report, status=ReportStatus.dismissed, admin_id=admin.id)

    async with async_session_maker() as db:
        rows = await _load_open_reports(db)
        return HTMLResponse(
            content=str(admin_reports_page(request=request, rows=rows, fragment=True))
        )


@router.post(
    "/{report_id}/delete-content",
    response_model=None,
    name="post_report_delete_content",
)
async def post_report_delete_content(
    request: Request,
    report_id: int,
) -> HTMLResponse:
    """Take the reported content down and close every open report against it."""
    admin: User = request.state.user
    async with async_session_maker.begin() as db:
        report = await db.get(ContentReport, report_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")
        if report.target_type is not ReportTargetType.display_image:
            raise HTTPException(
                status_code=422, detail="That kind of content cannot be removed here."
            )

        image = await db.get(UserDisplayImage, report.target_id)
        if image is not None:
            image.deleted_at = utc_now()
            image.deleted_by_id = admin.id

        # Close the siblings too: they name a target that no longer renders, and
        # leaving them open means the queue keeps asking about content that's gone.
        await db.execute(
            update(ContentReport)
            .where(
                ContentReport.target_type == ReportTargetType.display_image,
                ContentReport.target_id == report.target_id,
                ContentReport.status == ReportStatus.open,
            )
            .values(
                status=ReportStatus.actioned,
                resolved_at=utc_now(),
                resolved_by_id=admin.id,
            )
        )

    async with async_session_maker() as db:
        rows = await _load_open_reports(db)
        return HTMLResponse(
            content=str(admin_reports_page(request=request, rows=rows, fragment=True))
        )

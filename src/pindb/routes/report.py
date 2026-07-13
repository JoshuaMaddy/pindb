"""User-facing content reporting: ``POST /report``.

Deliberately generic. ``target_type`` + ``target_id`` is a polymorphic pointer
with **no foreign key**, so a report can outlive — or dangle past — the row it
names. Every path that deletes a reportable row therefore has to close the
reports pointing at it; nothing cascades and no FK check will remind you. See
``database/erasure.py`` and ``routes/admin/reports.py``.

Reporting requires a signed-in account: it kills drive-by spam and gives the
unique constraint something to key on.
"""

from typing import Annotated

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy.dialects.postgresql import insert as pg_insert

from pindb.auth import AuthenticatedUser
from pindb.database import async_session_maker
from pindb.database.content_report import (
    MAX_REPORT_REASON_LENGTH,
    MIN_REPORT_REASON_LENGTH,
    ContentReport,
    ReportTargetType,
)
from pindb.database.user_display import UserDisplayImage
from pindb.htmx_toast import redirect_or_htmx_toast

router = APIRouter(tags=["report"])

# Only display images are reportable today; the enum carries the rest so the
# queue and the admin actions extend without a schema change.
_SUPPORTED_TARGETS: dict[ReportTargetType, type] = {
    ReportTargetType.display_image: UserDisplayImage,
}


@router.post("/report", response_model=None, name="post_content_report")
async def post_content_report(
    request: Request,
    current_user: AuthenticatedUser,
    target_type: Annotated[str, Form()],
    target_id: Annotated[int, Form()],
    reason: Annotated[str, Form()],
) -> HTMLResponse | RedirectResponse:
    if target_type not in ReportTargetType:
        raise HTTPException(status_code=422, detail="Unknown report target")
    resolved_type = ReportTargetType(target_type)
    model = _SUPPORTED_TARGETS.get(resolved_type)
    if model is None:
        raise HTTPException(
            status_code=422, detail="That kind of content cannot be reported yet."
        )

    cleaned = reason.strip()
    if len(cleaned) < MIN_REPORT_REASON_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Tell us a bit more — at least {MIN_REPORT_REASON_LENGTH} characters."
            ),
        )
    cleaned = cleaned[:MAX_REPORT_REASON_LENGTH]

    async with async_session_maker.begin() as db:
        if await db.get(model, target_id) is None:
            raise HTTPException(status_code=404, detail="Content not found")
        # A second report from the same person on the same target adds nothing an
        # admin can act on, so the unique constraint absorbs it silently rather
        # than 500ing or scolding the user.
        await db.execute(
            pg_insert(ContentReport)
            .values(
                target_type=resolved_type.value,
                target_id=target_id,
                reason=cleaned,
                reporter_id=current_user.id,
            )
            .on_conflict_do_nothing(
                constraint="uq_content_reports_reporter_target",
            )
        )

    return redirect_or_htmx_toast(
        request=request,
        redirect_url=str(request.headers.get("Referer") or "/"),
        message="Thanks — an admin will take a look.",
    )

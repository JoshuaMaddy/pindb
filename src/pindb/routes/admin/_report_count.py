"""Open-report count for the admin panel badge."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.database.content_report import ContentReport, ReportStatus


async def count_open_reports(session: AsyncSession) -> int:
    total = await session.scalar(
        select(func.count())
        .select_from(ContentReport)
        .where(ContentReport.status == ReportStatus.open)
    )
    return total or 0

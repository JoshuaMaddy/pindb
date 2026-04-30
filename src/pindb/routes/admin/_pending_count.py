"""
FastAPI routes: `routes/admin/_pending_count.py`.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.database import Artist, Pin, PinSet, Shop, Tag
from pindb.database.pending_edit import PendingEdit


async def count_pending(session: AsyncSession) -> int:
    opts: dict[str, bool] = {"include_pending": True}
    total = 0
    for model in [Pin, Shop, Artist, Tag, PinSet]:
        count = await session.scalar(
            select(func.count())
            .select_from(model)
            .where(
                model.approved_at.is_(None),  # type: ignore[attr-defined]
                model.rejected_at.is_(None),  # type: ignore[attr-defined]
                model.deleted_at.is_(None),  # type: ignore[attr-defined]
            )
            .execution_options(**opts)  # type: ignore[arg-type]
        )
        total += count or 0

    edit_group_subq = (
        select(PendingEdit.entity_type, PendingEdit.entity_id)
        .where(
            PendingEdit.approved_at.is_(None),
            PendingEdit.rejected_at.is_(None),
        )
        .distinct()
        .subquery()
    )
    edit_group_count = await session.scalar(
        select(func.count()).select_from(edit_group_subq)
    )
    total += edit_group_count or 0
    return total

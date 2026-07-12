"""add rejection_reason to PendingMixin entities and pending_edits

Revision ID: d8e2f10b47c3
Revises: 957a10c31cfe
Create Date: 2026-07-11
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d8e2f10b47c3"
down_revision: Union[str, None] = "957a10c31cfe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The five PendingMixin tables, plus pending_edits, which declares the same
# approval columns by hand rather than through the mixin.
_TABLES: tuple[str, ...] = (
    "pins",
    "shops",
    "artists",
    "tags",
    "pin_sets",
    "pending_edits",
)


def upgrade() -> None:
    for table_name in _TABLES:
        op.add_column(
            table_name,
            sa.Column("rejection_reason", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    for table_name in _TABLES:
        op.drop_column(table_name, "rejection_reason")

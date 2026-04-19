"""add bulk_id to PendingMixin entities and pending_edits

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-04-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PENDING_TABLES: tuple[str, ...] = (
    "pins",
    "shops",
    "artists",
    "tags",
    "pin_sets",
)


def upgrade() -> None:
    for table_name in _PENDING_TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "bulk_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_index(
            op.f(f"ix_{table_name}_bulk_id"),
            table_name,
            ["bulk_id"],
            unique=False,
        )

    op.add_column(
        "pending_edits",
        sa.Column(
            "bulk_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_pending_edits_bulk_id"),
        "pending_edits",
        ["bulk_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_pending_edits_bulk_id"), table_name="pending_edits")
    op.drop_column("pending_edits", "bulk_id")
    for table_name in _PENDING_TABLES:
        op.drop_index(op.f(f"ix_{table_name}_bulk_id"), table_name=table_name)
        op.drop_column(table_name, "bulk_id")

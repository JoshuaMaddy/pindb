"""add_editor_role_and_pending_state

Revision ID: b7c3d4e5f6a2
Revises: a3f8b2c91d4e
Create Date: 2026-04-11

Adds an `is_editor` boolean to users and four approval-state columns
(approved_at, approved_by_id, rejected_at, rejected_by_id) to the six
editor-creatable entity tables: pins, shops, artists, tags, materials, pin_sets.

Existing rows are backfilled so that all previously-approved entities
(i.e. everything that wasn't soft-deleted) have approved_at = created_at
and approved_by_id = created_by_id. Newly created rows start with
approved_at = NULL (pending) unless the creator is an admin, which is
handled at the application layer.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c3d4e5f6a2"
down_revision: Union[str, None] = "a3f8b2c91d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that receive the four pending-state columns
_PENDING_TABLES: list[str] = [
    "pins",
    "shops",
    "artists",
    "tags",
    "materials",
    "pin_sets",
]


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_editor to users
    op.add_column(
        "users",
        sa.Column("is_editor", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Add approval columns to each pending entity table
    for table in _PENDING_TABLES:
        op.add_column(table, sa.Column("approved_at", sa.DateTime(), nullable=True))
        op.add_column(table, sa.Column("approved_by_id", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("rejected_at", sa.DateTime(), nullable=True))
        op.add_column(table, sa.Column("rejected_by_id", sa.Integer(), nullable=True))

    # Add FK constraints for approved_by_id and rejected_by_id
    for table in _PENDING_TABLES:
        op.create_foreign_key(
            f"fk_{table}_approved_by_id_users",
            table,
            "users",
            ["approved_by_id"],
            ["id"],
        )
        op.create_foreign_key(
            f"fk_{table}_rejected_by_id_users",
            table,
            "users",
            ["rejected_by_id"],
            ["id"],
        )

    # Backfill: mark all existing non-deleted rows as approved
    # (they were all curated before the editor system existed)
    conn = op.get_bind()
    for table in _PENDING_TABLES:
        conn.execute(
            sa.text(
                f"UPDATE {table} "
                "SET approved_at = created_at, approved_by_id = created_by_id "
                "WHERE deleted_at IS NULL"
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop FK constraints
    for table in _PENDING_TABLES:
        op.drop_constraint(
            f"fk_{table}_rejected_by_id_users", table, type_="foreignkey"
        )
        op.drop_constraint(
            f"fk_{table}_approved_by_id_users", table, type_="foreignkey"
        )

    # Drop approval columns
    for table in _PENDING_TABLES:
        op.drop_column(table, "rejected_by_id")
        op.drop_column(table, "rejected_at")
        op.drop_column(table, "approved_by_id")
        op.drop_column(table, "approved_at")

    # Drop is_editor from users
    op.drop_column("users", "is_editor")

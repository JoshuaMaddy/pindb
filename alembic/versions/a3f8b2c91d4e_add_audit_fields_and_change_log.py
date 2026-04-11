"""add_audit_fields_and_change_log

Revision ID: a3f8b2c91d4e
Revises: dd2ee36584ee
Create Date: 2026-04-11

Adds six audit columns (created_at, created_by_id, updated_at, updated_by_id,
deleted_at, deleted_by_id) to all core entity tables and creates the change_log
table for linear patch history. All new columns are nullable — existing rows
get NULL values and no backfill is required.

The users table already has created_at, so only the five remaining columns
are added there.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a3f8b2c91d4e"
down_revision: Union[str, None] = "dd2ee36584ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that get all six audit columns (created_at is new for all of them)
_FULL_AUDIT_TABLES: list[str] = [
    "pins",
    "artists",
    "shops",
    "tags",
    "materials",
    "grades",
    "pin_sets",
    "links",
    "currencies",
    "user_owned_pins",
    "user_wanted_pins",
    "user_auth_providers",
]

# Tables that get only five columns (created_at already exists)
_PARTIAL_AUDIT_TABLES: list[str] = ["users"]


def upgrade() -> None:
    """Upgrade schema."""
    # Add all six audit columns to tables that don't have any yet
    for table in _FULL_AUDIT_TABLES:
        op.add_column(table, sa.Column("created_at", sa.DateTime(), nullable=True))
        op.add_column(table, sa.Column("created_by_id", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("updated_at", sa.DateTime(), nullable=True))
        op.add_column(table, sa.Column("updated_by_id", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(), nullable=True))
        op.add_column(table, sa.Column("deleted_by_id", sa.Integer(), nullable=True))

    # Add five audit columns to users (created_at already exists)
    for table in _PARTIAL_AUDIT_TABLES:
        op.add_column(table, sa.Column("created_by_id", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("updated_at", sa.DateTime(), nullable=True))
        op.add_column(table, sa.Column("updated_by_id", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(), nullable=True))
        op.add_column(table, sa.Column("deleted_by_id", sa.Integer(), nullable=True))

    # Create change_log table
    op.create_table(
        "change_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("patch", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["changed_by_id"],
            ["users.id"],
            name=op.f("fk_change_log_changed_by_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_change_log")),
    )

    # Add FK constraints for audit columns on all tables
    all_tables = _FULL_AUDIT_TABLES + _PARTIAL_AUDIT_TABLES
    for table in all_tables:
        op.create_foreign_key(
            f"fk_{table}_created_by_id_users",
            table,
            "users",
            ["created_by_id"],
            ["id"],
        )
        op.create_foreign_key(
            f"fk_{table}_updated_by_id_users",
            table,
            "users",
            ["updated_by_id"],
            ["id"],
        )
        op.create_foreign_key(
            f"fk_{table}_deleted_by_id_users",
            table,
            "users",
            ["deleted_by_id"],
            ["id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    all_tables = _FULL_AUDIT_TABLES + _PARTIAL_AUDIT_TABLES

    # Drop FK constraints
    for table in all_tables:
        op.drop_constraint(f"fk_{table}_deleted_by_id_users", table, type_="foreignkey")
        op.drop_constraint(f"fk_{table}_updated_by_id_users", table, type_="foreignkey")
        op.drop_constraint(f"fk_{table}_created_by_id_users", table, type_="foreignkey")

    # Drop change_log table
    op.drop_table("change_log")

    # Drop audit columns from tables with all six
    for table in _FULL_AUDIT_TABLES:
        op.drop_column(table, "deleted_by_id")
        op.drop_column(table, "deleted_at")
        op.drop_column(table, "updated_by_id")
        op.drop_column(table, "updated_at")
        op.drop_column(table, "created_by_id")
        op.drop_column(table, "created_at")

    # Drop five audit columns from users (keep created_at)
    for table in _PARTIAL_AUDIT_TABLES:
        op.drop_column(table, "deleted_by_id")
        op.drop_column(table, "deleted_at")
        op.drop_column(table, "updated_by_id")
        op.drop_column(table, "updated_at")
        op.drop_column(table, "created_by_id")

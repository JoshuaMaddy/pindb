"""add normalized name generated columns

Revision ID: d3e4f5a6b7c8
Revises: c0d1e2f3a4b5
Create Date: 2026-04-27

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c0d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NORMALIZED_NAME_SQL = "replace(lower(btrim(name)), ' ', '_')"


def _normalized_column() -> sa.Column[str]:
    return sa.Column(
        "normalized_name",
        sa.Text(),
        sa.Computed(sqltext=_NORMALIZED_NAME_SQL, persisted=True),
        nullable=True,
    )


def upgrade() -> None:
    """Add generated normalized-name columns and lookup indexes."""
    for table_name in ("artists", "pins", "pin_sets", "shops", "tags"):
        op.add_column(table_name=table_name, column=_normalized_column())

    op.create_index(
        "ix_artists_normalized_name",
        "artists",
        ["normalized_name"],
    )
    op.create_index(
        "ix_pins_normalized_name",
        "pins",
        ["normalized_name"],
    )
    op.create_index(
        "ix_pin_sets_owner_normalized_name",
        "pin_sets",
        ["owner_id", "normalized_name"],
    )
    op.create_index(
        "ix_pin_sets_global_normalized_name",
        "pin_sets",
        ["normalized_name"],
        postgresql_where=sa.text("owner_id IS NULL AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_shops_normalized_name_active",
        "shops",
        ["normalized_name"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_tags_normalized_name_active",
        "tags",
        ["normalized_name"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Drop normalized-name lookup indexes and columns."""
    op.drop_index("ix_tags_normalized_name_active", table_name="tags")
    op.drop_index("ix_shops_normalized_name_active", table_name="shops")
    op.drop_index("ix_pin_sets_global_normalized_name", table_name="pin_sets")
    op.drop_index("ix_pin_sets_owner_normalized_name", table_name="pin_sets")
    op.drop_index("ix_pins_normalized_name", table_name="pins")
    op.drop_index("ix_artists_normalized_name", table_name="artists")

    for table_name in ("tags", "shops", "pin_sets", "pins", "artists"):
        op.drop_column(table_name=table_name, column_name="normalized_name")

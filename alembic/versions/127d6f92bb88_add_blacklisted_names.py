"""add blacklisted names

Purely additive: one new table, no ALTER on anything that exists, no PG enum
type (the enum column is a ``native_enum=False`` VARCHAR). A container running
the previous release never touches it, so this is safe to apply during the
blue/green overlap.

Revision ID: 127d6f92bb88
Revises: 91298792a7b1
Create Date: 2026-07-23 21:48:52.539249

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "127d6f92bb88"
down_revision: Union[str, Sequence[str], None] = "91298792a7b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "blacklisted_names",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "entity_type",
            sa.Enum(
                "shop",
                "artist",
                name="blacklistentitytype",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "normalized_name",
            sa.Text(),
            sa.Computed("replace(lower(btrim(name)), ' ', '_')", persisted=True),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_blacklisted_names_created_by_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blacklisted_names")),
    )
    op.create_index(
        "uq_blacklisted_names_entity_type_normalized_name",
        "blacklisted_names",
        ["entity_type", "normalized_name"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_blacklisted_names_entity_type_normalized_name",
        table_name="blacklisted_names",
    )
    op.drop_table("blacklisted_names")

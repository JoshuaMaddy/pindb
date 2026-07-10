"""add user stats and achievements

Revision ID: 957a10c31cfe
Revises: 49abc5a26a29
Create Date: 2026-07-10 14:39:21.311192

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "957a10c31cfe"
down_revision: Union[str, Sequence[str], None] = "49abc5a26a29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STAT_COLUMNS: tuple[str, ...] = (
    "pins_created",
    "unique_pins_edited",
    "unique_other_pins_edited",
    "tags_created",
    "unique_tags_edited",
    "unique_other_tags_edited",
    "shops_created",
    "unique_shops_edited",
    "unique_other_shops_edited",
    "artists_created",
    "unique_artists_edited",
    "unique_other_artists_edited",
    "global_sets_created",
    "pins_favorited",
    "pins_owned",
    "pins_wanted",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_stats",
        sa.Column("user_id", sa.Integer(), nullable=False),
        *(
            sa.Column(name, sa.Integer(), nullable=False, server_default="0")
            for name in _STAT_COLUMNS
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_stats_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user_stats")),
    )
    op.create_table(
        "user_achievements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("family", sa.String(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("achieved_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_achievements_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_achievements")),
        sa.UniqueConstraint(
            "user_id",
            "family",
            "tier",
            name="uq_user_achievements_user_id_family_tier",
        ),
    )
    op.create_index(
        op.f("ix_user_achievements_user_id"),
        "user_achievements",
        ["user_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_achievements_user_id"), table_name="user_achievements")
    op.drop_table("user_achievements")
    op.drop_table("user_stats")

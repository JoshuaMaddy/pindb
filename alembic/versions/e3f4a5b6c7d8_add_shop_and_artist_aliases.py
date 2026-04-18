"""add shop and artist alias tables

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-04-17
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shop_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["shop_id"],
            ["shops.id"],
            name=op.f("fk_shop_aliases_shop_id_shops"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shop_aliases")),
        sa.UniqueConstraint("alias", name=op.f("uq_shop_aliases_alias")),
    )
    op.create_table(
        "artist_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("artist_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artist_id"],
            ["artists.id"],
            name=op.f("fk_artist_aliases_artist_id_artists"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artist_aliases")),
        sa.UniqueConstraint("alias", name=op.f("uq_artist_aliases_alias")),
    )


def downgrade() -> None:
    op.drop_table("artist_aliases")
    op.drop_table("shop_aliases")

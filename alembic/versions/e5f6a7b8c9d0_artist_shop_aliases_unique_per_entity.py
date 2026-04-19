"""artist_aliases / shop_aliases: unique per (entity_id, alias)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-18

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("uq_shop_aliases_alias"),
        "shop_aliases",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_shop_aliases_shop_id_alias"),
        "shop_aliases",
        ["shop_id", "alias"],
    )
    op.drop_constraint(
        op.f("uq_artist_aliases_alias"),
        "artist_aliases",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_artist_aliases_artist_id_alias"),
        "artist_aliases",
        ["artist_id", "alias"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("uq_shop_aliases_shop_id_alias"),
        "shop_aliases",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_shop_aliases_alias"),
        "shop_aliases",
        ["alias"],
    )
    op.drop_constraint(
        op.f("uq_artist_aliases_artist_id_alias"),
        "artist_aliases",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_artist_aliases_alias"),
        "artist_aliases",
        ["alias"],
    )

"""tag_aliases: unique per (tag_id, alias), not globally on alias

Revision ID: d4e5f6a7b8c9
Revises: a5b6c7d8e9f0
Create Date: 2026-04-18

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "a5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("uq_tag_aliases_alias"),
        "tag_aliases",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_tag_aliases_tag_id_alias"),
        "tag_aliases",
        ["tag_id", "alias"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("uq_tag_aliases_tag_id_alias"),
        "tag_aliases",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_tag_aliases_alias"),
        "tag_aliases",
        ["alias"],
    )

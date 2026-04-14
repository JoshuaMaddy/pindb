"""add_tag_aliases

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-04-13

Add tag_aliases table for storing alternate names for tags.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tag_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name=op.f("fk_tag_aliases_tag_id_tags"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tag_aliases")),
        sa.UniqueConstraint("alias", name=op.f("uq_tag_aliases_alias")),
    )


def downgrade() -> None:
    op.drop_table("tag_aliases")

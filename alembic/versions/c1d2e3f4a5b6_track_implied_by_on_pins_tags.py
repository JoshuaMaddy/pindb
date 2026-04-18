"""track implied_by on pins_tags

Revision ID: c1d2e3f4a5b6
Revises: 78b0f6a1ac52
Create Date: 2026-04-17 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "78b0f6a1ac52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "pins_tags",
        sa.Column(
            "implied_by_tag_id",
            sa.Integer(),
            sa.ForeignKey("tags.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("pins_tags", "implied_by_tag_id")

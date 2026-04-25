"""add user dimension_unit preference

Revision ID: b8c0d1e2f3a4
Revises: 96659d4bb506
Create Date: 2026-04-24

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b8c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "96659d4bb506"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "dimension_unit",
            sa.String(),
            server_default="mm",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "dimension_unit")

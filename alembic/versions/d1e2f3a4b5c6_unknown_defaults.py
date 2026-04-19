"""unknown_defaults

Revision ID: d1e2f3a4b5c6
Revises: c9d4e5f6a7b8
Create Date: 2026-04-12

Make grades.price nullable (unknown price) and insert the "Unknown"
sentinel currency (id=999, code=UNK) so pins can be created without
knowing their price or currency.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c9d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make grades.price nullable
    op.alter_column("grades", "price", existing_type=sa.Float(), nullable=True)

    # Insert the Unknown currency sentinel (id 999 is unused in ISO 4217)
    op.execute(
        sa.text(
            "INSERT INTO currencies (id, name, code, created_at) "
            "VALUES (999, 'Unknown', 'UNK', NOW()) "
            "ON CONFLICT (id) DO NOTHING"
        )
    )


def downgrade() -> None:
    # Remove Unknown currency
    op.execute(sa.text("DELETE FROM currencies WHERE id = 999"))

    # Restore NOT NULL — set any NULL prices to 0 first to avoid constraint violation
    op.execute(sa.text("UPDATE grades SET price = 0 WHERE price IS NULL"))
    op.alter_column("grades", "price", existing_type=sa.Float(), nullable=False)

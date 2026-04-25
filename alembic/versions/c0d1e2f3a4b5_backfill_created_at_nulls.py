"""backfill NULL created_at to 1999-01-01

Revision ID: c0d1e2f3a4b5
Revises: b8c0d1e2f3a4
Create Date: 2026-04-25

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c0d1e2f3a4b5"
down_revision: Union[str, Sequence[str], None] = "b8c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FALLBACK = "1999-01-01 00:00:00"

_TABLES = [
    "artists",
    "currencies",
    "grades",
    "links",
    "pins",
    "pin_sets",
    "shops",
    "tags",
    "users",
    "user_auth_providers",
    "user_owned_pins",
    "user_wanted_pins",
]


def upgrade() -> None:
    """Set created_at = 1999-01-01 where currently NULL."""
    for table in _TABLES:
        op.execute(
            sa.text(
                f"UPDATE {table} SET created_at = :fallback WHERE created_at IS NULL"
            ).bindparams(fallback=_FALLBACK)
        )


def downgrade() -> None:
    """Re-null rows that match the exact backfill sentinel."""
    for table in _TABLES:
        op.execute(
            sa.text(
                f"UPDATE {table} SET created_at = NULL WHERE created_at = :fallback"
            ).bindparams(fallback=_FALLBACK)
        )

"""add meta oauth provider and verified flags

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-04-17

Adds ``email_verified`` and ``provider_username`` columns to
``user_auth_providers``. Existing rows are backfilled so Google links keep
their implicit trust (``email_verified = TRUE``) while Discord rows default
to ``FALSE`` — operators can flip these later if they trust Discord's
``verified`` flag retroactively. The ``provider`` column is stored as a
non-native enum (plain string), so accepting the new ``meta`` value requires
no DDL; the StrEnum on the Python side is the source of truth.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_auth_providers",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "user_auth_providers",
        sa.Column("provider_username", sa.String(), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE user_auth_providers SET email_verified = TRUE "
            "WHERE provider = 'google'"
        )
    )


def downgrade() -> None:
    op.drop_column("user_auth_providers", "provider_username")
    op.drop_column("user_auth_providers", "email_verified")

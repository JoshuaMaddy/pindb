"""reconcile drift: created_at not null constraints

Revision ID: 49abc5a26a29
Revises: 8ec5d4451612
Create Date: 2026-07-07 17:58:19.995878

Reconciles pre-existing schema drift between the migrations and the ORM models:
``AuditMixin.created_at`` is non-optional (NOT NULL) in the models, but these
tables were left nullable. NULLs were already backfilled to 1999-01-01 by
revision c0d1e2f3a4b5; this defensively re-backfills (idempotent) and then adds
the NOT NULL constraint so ``alembic check`` matches the models.

``users`` is intentionally excluded — its ``created_at`` is already NOT NULL.

Blue/green safety: adding NOT NULL here is safe because ``AuditMixin`` always
populates ``created_at`` (audit ``before_flush``), so a concurrently-running old
container never writes NULL during the deploy swap.
"""

from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "49abc5a26a29"
down_revision: Union[str, Sequence[str], None] = "8ec5d4451612"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FALLBACK = datetime(1999, 1, 1, 0, 0, 0)

# Tables whose created_at is still nullable in the DB but NOT NULL in the models.
# (Same set as the c0d1e2f3a4b5 backfill minus ``users``, already NOT NULL.)
_TABLES = [
    "artists",
    "currencies",
    "grades",
    "links",
    "pins",
    "pin_sets",
    "shops",
    "tags",
    "user_auth_providers",
    "user_owned_pins",
    "user_wanted_pins",
]


def upgrade() -> None:
    """Backfill any residual NULLs, then set ``created_at`` NOT NULL."""
    for table in _TABLES:
        op.execute(
            sa.text(
                f"UPDATE {table} SET created_at = :fallback WHERE created_at IS NULL"
            ).bindparams(fallback=_FALLBACK)
        )
        op.alter_column(
            table,
            "created_at",
            existing_type=sa.DateTime(),
            nullable=False,
        )


def downgrade() -> None:
    """Revert ``created_at`` to nullable."""
    for table in _TABLES:
        op.alter_column(
            table,
            "created_at",
            existing_type=sa.DateTime(),
            nullable=True,
        )

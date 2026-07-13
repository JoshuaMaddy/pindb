"""add pay_for_production to fundingtype enum

``fundingtype`` (unlike the user-display enums) is a native Postgres ENUM
(``sa.Enum(..., name="fundingtype")`` with no ``native_enum=False`` in the
initial migration), so a new member needs ``ALTER TYPE ... ADD VALUE`` rather
than just a Python-side change. Purely additive — existing rows are untouched,
and old app code (unaware of the new member) never writes it, so this is safe
during the blue/green overlap: "add enum value" per CLAUDE.md migration
discipline.

Revision ID: 91298792a7b1
Revises: fc8470c7fd18
Create Date: 2026-07-12 23:05:14.911772

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "91298792a7b1"
down_revision: Union[str, Sequence[str], None] = "fc8470c7fd18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE fundingtype ADD VALUE 'pay_for_production'")


def downgrade() -> None:
    """Downgrade schema.

    Postgres has no ``DROP VALUE`` for enum types — removing one means
    rebuilding the type (create new type, cast the column over, drop the old
    type) and would fail outright if any row already uses the value. Not
    worth the ceremony for an additive migration; a real removal, if ever
    needed, should be its own migration written for that specific situation.
    """
    raise NotImplementedError(
        "Cannot drop a value from a Postgres enum type without rebuilding it "
        "— see docstring."
    )

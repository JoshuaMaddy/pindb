"""add pin variants and unauthorized copies

Revision ID: 96659d4bb506
Revises: e5f6a7b8c9d0
Create Date: 2026-04-24 15:27:46.580277

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "96659d4bb506"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "pin_variants",
        sa.Column("pin_id", sa.Integer(), nullable=False),
        sa.Column("variant_pin_id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "pin_id <> variant_pin_id",
            name=op.f("ck_pin_variants_pin_variants_no_self"),
        ),
        sa.ForeignKeyConstraint(
            ["pin_id"], ["pins.id"], name=op.f("fk_pin_variants_pin_id_pins")
        ),
        sa.ForeignKeyConstraint(
            ["variant_pin_id"],
            ["pins.id"],
            name=op.f("fk_pin_variants_variant_pin_id_pins"),
        ),
        sa.PrimaryKeyConstraint(
            "pin_id", "variant_pin_id", name=op.f("pk_pin_variants")
        ),
    )
    op.create_table(
        "pin_unauthorized_copies",
        sa.Column("pin_id", sa.Integer(), nullable=False),
        sa.Column("copy_pin_id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "pin_id <> copy_pin_id",
            name=op.f("ck_pin_unauthorized_copies_pin_unauthorized_copies_no_self"),
        ),
        sa.ForeignKeyConstraint(
            ["pin_id"],
            ["pins.id"],
            name=op.f("fk_pin_unauthorized_copies_pin_id_pins"),
        ),
        sa.ForeignKeyConstraint(
            ["copy_pin_id"],
            ["pins.id"],
            name=op.f("fk_pin_unauthorized_copies_copy_pin_id_pins"),
        ),
        sa.PrimaryKeyConstraint(
            "pin_id", "copy_pin_id", name=op.f("pk_pin_unauthorized_copies")
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("pin_unauthorized_copies")
    op.drop_table("pin_variants")

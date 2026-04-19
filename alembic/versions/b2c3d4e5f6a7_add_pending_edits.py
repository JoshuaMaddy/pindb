"""add_pending_edits

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-14

Add the pending_edits table that backs editor-submitted edits to canonical
entities (Pin / Shop / Artist / Tag / PinSet). Each row stores a JSONB patch
relative to the entity's effective state at submission time. Edits stack via
parent_id; approving the chain head applies the accumulated patch to the
canonical row.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_edits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "patch",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_by_id", sa.Integer(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["users.id"],
            name=op.f("fk_pending_edits_approved_by_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_pending_edits_created_by_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["pending_edits.id"],
            name=op.f("fk_pending_edits_parent_id_pending_edits"),
        ),
        sa.ForeignKeyConstraint(
            ["rejected_by_id"],
            ["users.id"],
            name=op.f("fk_pending_edits_rejected_by_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pending_edits")),
    )
    op.create_index(
        "ix_pending_edits_entity",
        "pending_edits",
        ["entity_type", "entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_pending_edits_open",
        "pending_edits",
        ["entity_type", "entity_id", "created_at"],
        unique=False,
        postgresql_where=sa.text("approved_at IS NULL AND rejected_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_pending_edits_open", table_name="pending_edits")
    op.drop_index("ix_pending_edits_entity", table_name="pending_edits")
    op.drop_table("pending_edits")

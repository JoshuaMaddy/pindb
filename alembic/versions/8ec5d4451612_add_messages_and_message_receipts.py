"""add messages and message_receipts

Revision ID: 8ec5d4451612
Revises: d3e4f5a6b7c8
Create Date: 2026-07-07 16:14:38.282594

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8ec5d4451612"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "system",
                "announcement",
                "direct",
                "contribution",
                "pin_rejection",
                name="messagecategory",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=True),
        sa.Column("recipient_id", sa.Integer(), nullable=True),
        sa.Column(
            "audience",
            sa.Enum(
                "all",
                "editors",
                "admins",
                name="messageaudience",
                native_enum=False,
            ),
            server_default="all",
            nullable=False,
        ),
        sa.Column(
            "related_entity_type",
            sa.Enum(
                "pin",
                "shop",
                "artist",
                "tag",
                "pin_set",
                name="entitytype",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("related_entity_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "(related_entity_type IS NULL) = (related_entity_id IS NULL)",
            name=op.f("ck_messages_related_entity_both_or_neither"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_messages_created_by_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by_id"],
            ["users.id"],
            name=op.f("fk_messages_deleted_by_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["messages.id"],
            name=op.f("fk_messages_parent_id_messages"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"],
            ["users.id"],
            name=op.f("fk_messages_recipient_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"],
            ["users.id"],
            name=op.f("fk_messages_sender_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_messages_updated_by_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    op.create_index(
        "ix_messages_recipient_active",
        "messages",
        ["recipient_id"],
        unique=False,
        postgresql_where="deleted_at IS NULL",
    )
    op.create_index(
        "ix_messages_related_entity",
        "messages",
        ["related_entity_type", "related_entity_id"],
        unique=False,
    )
    op.create_table(
        "message_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("seen_at", sa.DateTime(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name=op.f("fk_message_receipts_message_id_messages"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_message_receipts_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_message_receipts")),
        sa.UniqueConstraint(
            "message_id",
            "user_id",
            name="uq_message_receipts_message_id_user_id",
        ),
    )
    op.create_index(
        "ix_message_receipts_user_state",
        "message_receipts",
        ["user_id", "archived_at", "seen_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_message_receipts_user_state", table_name="message_receipts")
    op.drop_table("message_receipts")
    op.drop_index("ix_messages_related_entity", table_name="messages")
    op.drop_index(
        "ix_messages_recipient_active",
        table_name="messages",
        postgresql_where="deleted_at IS NULL",
    )
    op.drop_table("messages")

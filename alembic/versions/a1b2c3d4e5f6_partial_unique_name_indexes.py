"""partial_unique_name_indexes

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-04-13

Replace plain unique constraints on tags.name and shops.name with partial unique
indexes (WHERE deleted_at IS NULL) so soft-deleted rows don't block re-use of names.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_tags_name", "tags", type_="unique")
    op.create_index(
        "uq_tags_name_active",
        "tags",
        ["name"],
        unique=True,
        postgresql_where="deleted_at IS NULL",
    )

    op.drop_constraint("uq_shops_name", "shops", type_="unique")
    op.create_index(
        "uq_shops_name_active",
        "shops",
        ["name"],
        unique=True,
        postgresql_where="deleted_at IS NULL",
    )


def downgrade() -> None:
    op.drop_index("uq_shops_name_active", table_name="shops")
    op.create_unique_constraint("uq_shops_name", "shops", ["name"])

    op.drop_index("uq_tags_name_active", table_name="tags")
    op.create_unique_constraint("uq_tags_name", "tags", ["name"])

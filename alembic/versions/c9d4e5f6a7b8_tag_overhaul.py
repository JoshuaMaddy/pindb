"""tag_overhaul

Revision ID: c9d4e5f6a7b8
Revises: b7c3d4e5f6a2
Create Date: 2026-04-12

Tag system overhaul:
- Add category column to tags (VARCHAR, default 'general')
- Create tag_implications M2M join table (replaces parent_id hierarchy)
- Migrate existing parent_id relationships to tag_implications
- Drop parent_id from tags
- Migrate materials table rows to tags with category='material'
- Migrate pins_materials join rows to pins_tags
- Drop pins_materials and materials tables
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d4e5f6a7b8"
down_revision: Union[str, None] = "b7c3d4e5f6a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add category column to tags
    op.add_column(
        "tags",
        sa.Column(
            "category",
            sa.String(),
            nullable=False,
            server_default="general",
        ),
    )

    # 2. Create tag_implications join table
    op.create_table(
        "tag_implications",
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "implied_tag_id",
            sa.Integer(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )

    # 3. Migrate parent_id relationships to tag_implications
    op.execute(
        """
        INSERT INTO tag_implications (tag_id, implied_tag_id)
        SELECT id, parent_id
        FROM tags
        WHERE parent_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    # 4. Drop parent_id from tags
    op.drop_column("tags", "parent_id")

    # 5. Migrate materials -> tags with category='material'
    # Preserve all audit/pending fields; skip if name already exists as a tag
    op.execute(
        """
        INSERT INTO tags (
            name, category,
            created_at, created_by_id, updated_at, updated_by_id,
            deleted_at, deleted_by_id,
            approved_at, approved_by_id, rejected_at, rejected_by_id
        )
        SELECT
            name, 'material',
            created_at, created_by_id, updated_at, updated_by_id,
            deleted_at, deleted_by_id,
            approved_at, approved_by_id, rejected_at, rejected_by_id
        FROM materials
        ON CONFLICT (name) DO UPDATE SET category = 'material'
        """
    )

    # 6. Migrate pins_materials -> pins_tags
    op.execute(
        """
        INSERT INTO pins_tags (pin_id, tag_id)
        SELECT pm.pin_id, t.id
        FROM pins_materials pm
        JOIN materials m ON m.id = pm.material_id
        JOIN tags t ON t.name = m.name
        ON CONFLICT DO NOTHING
        """
    )

    # 7. Drop material tables
    op.drop_table("pins_materials")
    op.drop_table("materials")


def downgrade() -> None:
    # Recreate materials table
    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "deleted_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "approved_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "rejected_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Recreate pins_materials
    op.create_table(
        "pins_materials",
        sa.Column(
            "pin_id",
            sa.Integer(),
            sa.ForeignKey("pins.id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "material_id",
            sa.Integer(),
            sa.ForeignKey("materials.id"),
            primary_key=True,
            nullable=False,
        ),
    )

    # Restore material-category tags back to materials table
    op.execute(
        """
        INSERT INTO materials (
            name,
            created_at, created_by_id, updated_at, updated_by_id,
            deleted_at, deleted_by_id,
            approved_at, approved_by_id, rejected_at, rejected_by_id
        )
        SELECT
            name,
            created_at, created_by_id, updated_at, updated_by_id,
            deleted_at, deleted_by_id,
            approved_at, approved_by_id, rejected_at, rejected_by_id
        FROM tags
        WHERE category = 'material'
        """
    )

    # Restore pins_materials from pins_tags for material-category tags
    op.execute(
        """
        INSERT INTO pins_materials (pin_id, material_id)
        SELECT pt.pin_id, m.id
        FROM pins_tags pt
        JOIN tags t ON t.id = pt.tag_id AND t.category = 'material'
        JOIN materials m ON m.name = t.name
        ON CONFLICT DO NOTHING
        """
    )

    # Remove material-category tags from pins_tags
    op.execute(
        """
        DELETE FROM pins_tags
        WHERE tag_id IN (SELECT id FROM tags WHERE category = 'material')
        """
    )

    # Remove material-category tags
    op.execute("DELETE FROM tags WHERE category = 'material'")

    # Restore parent_id
    op.add_column(
        "tags",
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("tags.id"), nullable=True),
    )

    # Restore parent relationships from tag_implications
    op.execute(
        """
        UPDATE tags SET parent_id = ti.implied_tag_id
        FROM tag_implications ti
        WHERE tags.id = ti.tag_id
        """
    )

    # Drop tag_implications
    op.drop_table("tag_implications")

    # Drop category column
    op.drop_column("tags", "category")

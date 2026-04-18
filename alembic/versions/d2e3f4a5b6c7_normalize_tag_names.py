"""normalize tag names to e621 form (lowercase, spaces to underscores)

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-04-17
"""

from typing import Union

from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Normalize tag names: lowercase + spaces → underscores
    # Handles conflicts by keeping the lowest-id tag when names collide post-normalization.
    op.execute("""
        WITH normalized AS (
            SELECT id, LOWER(REPLACE(name, ' ', '_')) AS new_name
            FROM tags
            WHERE name != LOWER(REPLACE(name, ' ', '_'))
        ),
        keep AS (
            -- For each collision group, keep the tag with the lowest id
            SELECT DISTINCT ON (new_name) n.id, n.new_name
            FROM normalized n
            ORDER BY n.new_name, n.id ASC
        ),
        -- Also include tags already in normalized form that share a target name
        collision_targets AS (
            SELECT id, name AS new_name FROM tags
            WHERE name = LOWER(REPLACE(name, ' ', '_'))
              AND name IN (SELECT new_name FROM normalized)
        ),
        first_survivor AS (
            SELECT DISTINCT ON (new_name) id, new_name
            FROM (SELECT id, new_name FROM keep UNION ALL SELECT id, new_name FROM collision_targets) combined
            ORDER BY new_name, id ASC
        )
        UPDATE tags SET name = fs.new_name
        FROM first_survivor fs
        WHERE tags.id = fs.id
    """)

    # Normalize tag aliases
    op.execute("""
        UPDATE tag_aliases
        SET alias = LOWER(REPLACE(alias, ' ', '_'))
        WHERE alias != LOWER(REPLACE(alias, ' ', '_'))
    """)


def downgrade() -> None:
    pass  # normalization is not reversible

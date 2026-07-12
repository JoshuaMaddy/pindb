"""index join table reverse columns

Revision ID: a7f3c21e9b04
Revises: d8e2f10b47c3
Create Date: 2026-07-12

Every pin-facing join table's composite primary key leads with ``pin_id``, so it
can only serve lookups that start from a pin. The application almost always asks
the other direction — "which pins belong to this tag / shop / artist / set" — for
list pages, detail pages, and pin-count aggregates, and those were sequential
scans of the whole join table.

Built CONCURRENTLY inside an autocommit block: CREATE INDEX takes an ACCESS
EXCLUSIVE lock otherwise, which would block writes to the join tables for the
duration, and this migration runs against the live database while the old app
colour is still serving traffic.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a7f3c21e9b04"
down_revision: Union[str, None] = "d8e2f10b47c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEXES: tuple[tuple[str, str, str], ...] = (
    ("ix_pins_tags_tag_id", "pins_tags", "tag_id"),
    ("ix_pins_shops_shop_id", "pins_shops", "shop_id"),
    ("ix_pins_artists_artists_id", "pins_artists", "artists_id"),
    ("ix_pin_set_memberships_set_id", "pin_set_memberships", "set_id"),
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, column in _INDEXES:
            op.create_index(
                name,
                table,
                [column],
                postgresql_concurrently=True,
                if_not_exists=True,
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, _ in _INDEXES:
            op.drop_index(
                name,
                table_name=table,
                postgresql_concurrently=True,
                if_exists=True,
            )

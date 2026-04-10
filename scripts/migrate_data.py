"""
Migrate data from the Windows-native PostgreSQL instance to the dev Docker instance.

Usage:
    uv run scripts/migrate_data.py

Meilisearch will be re-indexed automatically on next app startup via update_all().
NOTE: Image files are NOT copied by this script — copy them manually:
    robocopy <source_image_directory> <dev_image_directory> /E
"""

import sys
from sqlalchemy import create_engine, text

SRC = "postgresql+psycopg://postgres:Pa$$i$cool1@localhost/postgres"
DST = "postgresql+psycopg://pindb:kjsdfhklyhuaJHjkfhdesf@localhost:5433/pindb"

# Tables in FK-safe insert order. Join tables last.
TABLES = [
    "currencies",
    "grades",
    "materials",
    "shops",
    "artists",
    "tags",  # self-referential parent_id — handled via deferred FK check
    "links",
    "users",
    "pins",
    "pin_sets",
    "user_sessions",
    "user_auth_providers",
    # join tables
    "artists_links",
    "shops_links",
    "pin_sets_links",
    "pins_links",
    "pins_artists",
    "pins_grades",
    "pins_materials",
    "pins_shops",
    "pins_tags",
    "pin_set_memberships",
    "user_favorite_pins",
    "user_favorite_pin_sets",
]


def migrate() -> None:
    src_engine = create_engine(SRC)
    dst_engine = create_engine(DST)

    with src_engine.connect() as src, dst_engine.connect() as dst:
        # Disable FK checks for the duration of the import
        dst.execute(text("SET session_replication_role = 'replica'"))

        for table in TABLES:
            rows = src.execute(text(f"SELECT * FROM {table}")).mappings().all()
            count = len(rows)

            if not rows:
                print(f"  {table}: empty, skipping")
                continue

            dst.execute(text(f"TRUNCATE {table} CASCADE"))

            cols = list(rows[0].keys())
            col_list = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(f":{c}" for c in cols)
            insert_sql = text(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
            )
            dst.execute(insert_sql, [dict(r) for r in rows])
            print(f"  {table}: {count} rows copied")

        # Restore FK checks
        dst.execute(text("SET session_replication_role = 'origin'"))

        # Reset sequences so new inserts get correct next IDs.
        # Query pg_class to find every sequence and its owning table+column.
        owned_seqs = (
            dst.execute(
                text("""
            SELECT
                t.relname  AS table_name,
                a.attname  AS col_name,
                s.relname  AS seq_name
            FROM pg_class s
            JOIN pg_depend d
                ON d.objid = s.oid
               AND d.classid = 'pg_class'::regclass
               AND d.refclassid = 'pg_class'::regclass
               AND d.deptype = 'a'
            JOIN pg_class t ON t.oid = d.refobjid
            JOIN pg_attribute a
                ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
            WHERE s.relkind = 'S'
              AND t.relnamespace = 'public'::regnamespace
        """)
            )
            .mappings()
            .all()
        )

        for row in owned_seqs:
            dst.execute(
                text(f"""
                SELECT setval(
                    'public.{row["seq_name"]}',
                    COALESCE((SELECT MAX({row["col_name"]}) FROM {row["table_name"]}), 1)
                )
            """)
            )
            print(f"  reset sequence: {row['seq_name']}")

        dst.commit()

    print("\nDone. Start the app to trigger Meilisearch re-indexing.")


if __name__ == "__main__":
    print(f"Source: {SRC}")
    print(f"Dest:   {DST}\n")
    try:
        migrate()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)

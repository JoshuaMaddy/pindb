#!/usr/bin/env python
"""Migrate images between filesystem and Cloudflare R2 backends.

Usage:
    uv run python scripts/migrate_images.py --direction fs-to-r2
    uv run python scripts/migrate_images.py --direction r2-to-fs

Both sets of credentials must be present in the environment / .env file
regardless of the current image_backend setting.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pindb.config import CONFIGURATION
from pindb.file_handler import (
    FilesystemBackend,
    R2Backend,
    THUMBNAIL_SUFFIX,
    _make_thumbnail_bytes,
)


def _r2_backend() -> R2Backend:
    missing = [
        f
        for f in (
            "r2_account_id",
            "r2_bucket",
            "r2_access_key_id",
            "r2_secret_access_key",
        )
        if getattr(CONFIGURATION, f) is None
    ]
    if missing:
        sys.exit(f"R2 credentials missing: {', '.join(missing)}")
    return R2Backend()


def _fs_backend() -> FilesystemBackend:
    if CONFIGURATION.image_directory is None:
        sys.exit("image_directory not set")
    return FilesystemBackend(CONFIGURATION.image_directory)


def migrate(
    source: FilesystemBackend | R2Backend,
    dest: FilesystemBackend | R2Backend,
) -> None:
    keys = source.list_keys()
    print(f"Found {len(keys)} images to migrate.")

    ok = skip = 0
    for i, key in enumerate(keys, 1):
        data = source.load(key)
        if data is None:
            print(f"  [{i}/{len(keys)}] SKIP {key} — not found in source")
            skip += 1
            continue

        dest.save(key, data)

        thumb_key = f"{key}{THUMBNAIL_SUFFIX}"
        thumb_data = source.load(thumb_key)
        if thumb_data is None:
            thumb_data = _make_thumbnail_bytes(data)
        dest.save(thumb_key, thumb_data)

        print(f"  [{i}/{len(keys)}] OK   {key}")
        ok += 1

    print(f"\nDone. {ok} migrated, {skip} skipped.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate PinDB images between backends"
    )
    parser.add_argument(
        "--direction",
        choices=["fs-to-r2", "r2-to-fs"],
        required=True,
        help="fs-to-r2: upload filesystem images to R2. r2-to-fs: download R2 images to filesystem.",
    )
    args = parser.parse_args()

    if args.direction == "fs-to-r2":
        source: FilesystemBackend | R2Backend = _fs_backend()
        dest: FilesystemBackend | R2Backend = _r2_backend()
        print(
            f"Migrating filesystem ({CONFIGURATION.image_directory}) → R2 ({CONFIGURATION.r2_bucket})"
        )
    else:
        source = _r2_backend()
        dest = _fs_backend()
        print(
            f"Migrating R2 ({CONFIGURATION.r2_bucket}) → filesystem ({CONFIGURATION.image_directory})"
        )

    migrate(source, dest)


if __name__ == "__main__":
    main()

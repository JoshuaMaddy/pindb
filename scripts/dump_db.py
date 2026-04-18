"""
Full logical backup and restore of the PinDB PostgreSQL database.

By default, pg_dump / psql / pg_restore run **inside** the Compose Postgres service
(`--via-docker`, default on), matching the app's Docker DB connection and avoiding
local client tools.

With `--no-via-docker`, uses pg_dump / pg_restore / psql on your PATH. Requires
PostgreSQL client tools (same major version as the server is recommended).

Typical uses:
- Scheduled backups: point DATABASE_CONNECTION at production and write a .dump file.
- Seed a fresh Docker Postgres: create an empty database, then load a dump.

Usage:
    uv run scripts/dump_db.py dump -o backups/pindb.dump
    uv run scripts/dump_db.py load -i backups/pindb.dump

Local pg_* tools only (no docker exec):
    uv run scripts/dump_db.py dump -o backups/pindb.dump --no-via-docker
    uv run scripts/dump_db.py load -i backups/pindb.dump --no-via-docker

Override connection (no .env required):
    uv run scripts/dump_db.py dump -o out.dump \\
        --database-url postgresql+psycopg://pindb:pass@127.0.0.1:5433/pindb
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import make_url

_REPO_ROOT = Path(__file__).resolve().parent.parent

_COMPOSE_CANDIDATES = ("docker-compose.dev.yaml", "docker-compose.yaml")


class _DumpDbUrlSettings(BaseSettings):
    """DATABASE_CONNECTION and/or Compose-style POSTGRES_* (same as docker-compose)."""

    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        extra="ignore",
        case_sensitive=False,
    )

    database_connection: str | None = None
    postgres_user: str = Field(default="pindb")
    postgres_password: str | None = Field(default=None)
    postgres_db: str = Field(default="pindb")
    postgres_host: str = Field(default="postgres")
    postgres_port: int = Field(default=5432)


def _compose_default_database_url(settings: _DumpDbUrlSettings) -> str | None:
    """Same shape as the app container: postgresql+psycopg://...@postgres:5432/pindb."""
    pw = settings.postgres_password
    if pw is None or pw == "":
        return None
    password = quote_plus(pw)
    user = quote_plus(settings.postgres_user)
    host = settings.postgres_host
    port = settings.postgres_port
    db = settings.postgres_db
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


def _sqlalchemy_url_to_libpq(sqlalchemy_url: str) -> str:
    """Strip SQLAlchemy drivers (e.g. +psycopg) for libpq CLI tools."""
    u = make_url(sqlalchemy_url)
    return u.set(drivername="postgresql").render_as_string(hide_password=False)


def _require_cli_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        print(
            f"error: `{name}` not found on PATH.\n"
            "  Install PostgreSQL client tools (same major version as the server), or\n"
            "  from the repo root with Compose Postgres running: add --via-docker",
            file=sys.stderr,
        )
        sys.exit(1)
    return path


def _require_docker() -> str:
    path = shutil.which("docker")
    if path is None:
        print(
            "error: `docker` not found on PATH. Install Docker Desktop or use local pg_* tools.",
            file=sys.stderr,
        )
        sys.exit(1)
    return path


def _default_compose_file() -> Path | None:
    for name in _COMPOSE_CANDIDATES:
        p = _REPO_ROOT / name
        if p.is_file():
            return p
    return None


def _resolve_compose_file(args: argparse.Namespace) -> Path:
    raw = getattr(args, "compose_file", None)
    if raw is not None:
        cp = Path(raw).expanduser().resolve()
        if not cp.is_file():
            print(f"error: compose file not found: {cp}", file=sys.stderr)
            sys.exit(1)
        return cp
    dc = _default_compose_file()
    if dc is None:
        print(
            f"error: no compose file in repo root ({', '.join(_COMPOSE_CANDIDATES)}).\n"
            "  Pass --compose-file path/to/docker-compose.yaml",
            file=sys.stderr,
        )
        sys.exit(1)
    return dc


def _cmd_dump_docker(args: argparse.Namespace, *, out: Path) -> None:
    _require_docker()
    compose = _resolve_compose_file(args)
    service: str = args.docker_service
    verbose_flag = " -v" if args.verbose else ""

    if args.format == "plain":
        inner = (
            "set -eu\n"
            'export PGPASSWORD="$POSTGRES_PASSWORD"\n'
            f'pg_dump -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
            f"-Fp --no-owner --no-acl{verbose_flag}\n"
        )
    else:
        inner = (
            "set -eu\n"
            'export PGPASSWORD="$POSTGRES_PASSWORD"\n'
            f'pg_dump -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
            f"-Fc --no-owner --no-acl --compress={args.compress}{verbose_flag}\n"
        )

    cmd = [
        "docker",
        "compose",
        "-f",
        str(compose),
        "exec",
        "-T",
        service,
        "sh",
        "-c",
        inner,
    ]
    print(
        f"Running: docker compose -f {compose.name} exec {service} pg_dump -> {out}",
        file=sys.stderr,
    )
    proc = subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        cwd=_REPO_ROOT,
    )
    out.write_bytes(proc.stdout)


def _cmd_load_docker(args: argparse.Namespace, *, dump_path: Path) -> None:
    _require_docker()
    compose = _resolve_compose_file(args)
    service: str = args.docker_service
    data = dump_path.read_bytes()

    effective_format: Literal["custom", "plain"]
    if args.format == "auto":
        effective_format = _guess_dump_format(dump_path)
    else:
        effective_format = args.format

    if effective_format == "plain":
        extra = " --echo-all" if args.verbose else ""
        inner = (
            "set -eu\n"
            'export PGPASSWORD="$POSTGRES_PASSWORD"\n'
            f'psql -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
            f"--echo-errors -v ON_ERROR_STOP=1{extra} -f -\n"
        )
    else:
        clean_part = "--clean --if-exists" if args.clean else ""
        verbose_part = "-v" if args.verbose else ""
        if args.jobs > 1:
            print(
                "warning: pg_restore parallel mode is disabled when using stdin; using 1 job",
                file=sys.stderr,
            )
        inner = (
            "set -eu\n"
            'export PGPASSWORD="$POSTGRES_PASSWORD"\n'
            f'pg_restore -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
            f"--no-owner --no-acl {clean_part} {verbose_part} -\n"
        )

    cmd = [
        "docker",
        "compose",
        "-f",
        str(compose),
        "exec",
        "-T",
        service,
        "sh",
        "-c",
        inner,
    ]
    print(
        f"Running: docker compose -f {compose.name} exec {service} "
        f"{'psql' if effective_format == 'plain' else 'pg_restore'} <- {dump_path}",
        file=sys.stderr,
    )
    subprocess.run(
        cmd,
        input=data,
        check=True,
        cwd=_REPO_ROOT,
    )


def _resolve_database_url(args: argparse.Namespace) -> str:
    if args.database_url is not None:
        return args.database_url
    settings = _DumpDbUrlSettings.model_validate({})
    if settings.database_connection and settings.database_connection.strip():
        return settings.database_connection
    built = _compose_default_database_url(settings)
    if built is not None:
        return built
    print(
        "error: could not resolve a database URL.\n"
        "  Set DATABASE_CONNECTION or POSTGRES_PASSWORD in the environment / .env, or\n"
        "  pass --database-url (Compose default: postgresql+psycopg://...@postgres:5432/pindb).",
        file=sys.stderr,
    )
    sys.exit(1)


def _guess_dump_format(path: Path) -> Literal["custom", "plain"]:
    suf = path.suffix.lower()
    if suf in {".sql", ".pgsql"}:
        return "plain"
    if suf in {".dump", ".backup", ".custom"}:
        return "custom"
    with path.open("rb") as f:
        magic = f.read(5)
    if magic == b"PGDMP":
        return "custom"
    return "plain"


def _cmd_dump(args: argparse.Namespace) -> None:
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.via_docker:
        _cmd_dump_docker(args, out=out)
        return

    libpq_url = _sqlalchemy_url_to_libpq(_resolve_database_url(args))
    pg_dump = _require_cli_tool("pg_dump")
    if args.format == "plain":
        cmd: list[str] = [
            pg_dump,
            f"--dbname={libpq_url}",
            "--format=plain",
            f"--file={out}",
            "--no-owner",
            "--no-acl",
        ]
        if args.verbose:
            cmd.append("--verbose")
    else:
        cmd = [
            pg_dump,
            f"--dbname={libpq_url}",
            "--format=custom",
            f"--file={out}",
            "--no-owner",
            "--no-acl",
        ]
        cmd.append(f"--compress={args.compress}")
        if args.verbose:
            cmd.append("--verbose")

    print(f"Running: {Path(pg_dump).name} (output: {out})", file=sys.stderr)
    subprocess.run(cmd, check=True)


def _cmd_load(args: argparse.Namespace) -> None:
    dump_path = Path(args.input).expanduser().resolve()

    if not dump_path.is_file():
        print(f"error: not a file: {dump_path}", file=sys.stderr)
        sys.exit(1)

    if args.via_docker:
        _cmd_load_docker(args, dump_path=dump_path)
        return

    libpq_url = _sqlalchemy_url_to_libpq(_resolve_database_url(args))

    effective_format: Literal["custom", "plain"]
    if args.format == "auto":
        effective_format = _guess_dump_format(dump_path)
    else:
        effective_format = args.format

    if effective_format == "plain":
        psql = _require_cli_tool("psql")
        cmd = [
            psql,
            f"--dbname={libpq_url}",
            "--echo-errors",
            "--variable=ON_ERROR_STOP=1",
            f"--file={dump_path}",
        ]
        if args.verbose:
            cmd.append("--echo-all")
        print(f"Running: {Path(psql).name} (input: {dump_path})", file=sys.stderr)
        subprocess.run(cmd, check=True)
        return

    pg_restore = _require_cli_tool("pg_restore")
    cmd: list[str] = [
        pg_restore,
        f"--dbname={libpq_url}",
        "--no-owner",
        "--no-acl",
    ]
    if args.clean:
        cmd.append("--clean")
        cmd.append("--if-exists")
    if args.jobs and args.jobs > 1:
        cmd.append(f"--jobs={args.jobs}")
    if args.verbose:
        cmd.append("--verbose")
    cmd.append(str(dump_path))

    print(f"Running: {Path(pg_restore).name} (input: {dump_path})", file=sys.stderr)
    subprocess.run(cmd, check=True)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Dump or load the PinDB Postgres database (pg_dump / pg_restore / psql).",
    )
    p.add_argument(
        "--database-url",
        dest="database_url",
        default=None,
        help="SQLAlchemy URL (e.g. postgresql+psycopg://...). Overrides DATABASE_CONNECTION / .env.",
    )

    sub = p.add_subparsers(dest="command", required=True)

    dump_p = sub.add_parser("dump", help="Write a full database dump to a file.")
    dump_p.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output path (.dump recommended for custom format).",
    )
    dump_p.add_argument(
        "--format",
        choices=("custom", "plain"),
        default="custom",
        help="custom: pg_dump -Fc (default). plain: SQL script for psql.",
    )
    dump_p.add_argument(
        "--compress",
        type=int,
        default=9,
        metavar="N",
        help="gzip compression for custom format (0-9). Default: 9. Use 0 to disable.",
    )
    dump_p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Pass --verbose to pg_dump.",
    )
    dump_p.add_argument(
        "--via-docker",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run pg_dump in the Compose postgres container (default: true). "
        "Use --no-via-docker for a local pg_dump on PATH.",
    )
    dump_p.add_argument(
        "--compose-file",
        default=None,
        metavar="PATH",
        help="Compose file (default: docker-compose.dev.yaml or docker-compose.yaml in repo root).",
    )
    dump_p.add_argument(
        "--docker-service",
        default="postgres",
        help="Compose service name for Postgres (default: postgres).",
    )
    dump_p.set_defaults(func=_cmd_dump)

    load_p = sub.add_parser(
        "load",
        help="Restore from a pg_dump file (custom or plain SQL).",
    )
    load_p.add_argument(
        "-i",
        "--input",
        required=True,
        help="Dump file from dump_db.py dump (or compatible pg_dump output).",
    )
    load_p.add_argument(
        "--format",
        choices=("auto", "custom", "plain"),
        default="auto",
        help="auto: infer from file extension / content (default).",
    )
    load_p.add_argument(
        "--clean",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Drop existing objects before restore (pg_restore only). Default: true.",
    )
    load_p.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=1,
        metavar="N",
        help="Parallel jobs for pg_restore (custom format only). Default: 1.",
    )
    load_p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Pass --verbose to pg_restore or --echo-all to psql.",
    )
    load_p.add_argument(
        "--via-docker",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run psql/pg_restore in the Compose postgres container (default: true). "
        "Use --no-via-docker for local psql/pg_restore on PATH.",
    )
    load_p.add_argument(
        "--compose-file",
        default=None,
        metavar="PATH",
        help="Compose file (default: docker-compose.dev.yaml or docker-compose.yaml in repo root).",
    )
    load_p.add_argument(
        "--docker-service",
        default="postgres",
        help="Compose service name for Postgres (default: postgres).",
    )
    load_p.set_defaults(func=_cmd_load)

    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

"""Add await to ORM session calls; async def for route handlers. Run: uv run python scripts/fix_async_routes.py"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src" / "pindb"

PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<![\w.])session\.scalar\("), "await session.scalar("),
    (re.compile(r"(?<![\w.])db\.scalar\("), "await db.scalar("),
    (re.compile(r"(?<![\w.])outer_session\.scalar\("), "await outer_session.scalar("),
    (re.compile(r"(?<![\w.])read_session\.scalar\("), "await read_session.scalar("),
    (re.compile(r"(?<![\w.])session\.scalars\("), "await session.scalars("),
    (re.compile(r"(?<![\w.])db\.scalars\("), "await db.scalars("),
    (re.compile(r"(?<![\w.])outer_session\.scalars\("), "await outer_session.scalars("),
    (re.compile(r"(?<![\w.])read_session\.scalars\("), "await read_session.scalars("),
    (re.compile(r"(?<![\w.])session\.get\("), "await session.get("),
    (re.compile(r"(?<![\w.])db\.get\("), "await db.get("),
    (re.compile(r"(?<![\w.])session\.execute\("), "await session.execute("),
    (re.compile(r"(?<![\w.])db\.execute\("), "await db.execute("),
    (re.compile(r"(?<![\w.])outer_session\.execute\("), "await outer_session.execute("),
    (re.compile(r"(?<![\w.])read_session\.execute\("), "await read_session.execute("),
    (re.compile(r"(?<![\w.])session\.commit\("), "await session.commit("),
    (re.compile(r"(?<![\w.])db\.commit\("), "await db.commit("),
    (re.compile(r"(?<![\w.])session\.delete\("), "await session.delete("),
    (re.compile(r"(?<![\w.])db\.delete\("), "await db.delete("),
    (re.compile(r"(?<![\w.])session\.refresh\("), "await session.refresh("),
    (re.compile(r"(?<![\w.])db\.refresh\("), "await db.refresh("),
    (re.compile(r"(?<![\w.])session\.merge\("), "await session.merge("),
    (re.compile(r"(?<![\w.])db\.merge\("), "await db.merge("),
    (re.compile(r"(?<![\w.])session\.flush\("), "await session.flush("),
    (re.compile(r"(?<![\w.])db\.flush\("), "await db.flush("),
]

ROUTE_DEF = re.compile(r"^(\s*)def (get_|post_|put_|patch_|delete_)")


def fix_text(text: str, *, do_route_async: bool) -> str:
    for pat, repl in PATTERNS:
        text = pat.sub(repl, text)
    if do_route_async:
        lines: list[str] = []
        for line in text.splitlines(keepends=True):
            if "async def" in line or not ROUTE_DEF.match(line):
                lines.append(line)
                continue
            if re.match(r"^\s*def _", line):
                lines.append(line)
                continue
            lines.append(re.sub(ROUTE_DEF, r"\1async def \2", line, count=1))
        text = "".join(lines)
    while "await await" in text:
        text = text.replace("await await", "await")
    return text


def main() -> int:
    n = 0
    files = list(ROOT.joinpath("routes").rglob("*.py")) + [ROOT / "__init__.py"]
    files += [ROOT / "database" / "erasure.py"]
    for path in files:
        if not path.is_file():
            continue
        old = path.read_text(encoding="utf-8")
        new = fix_text(old, do_route_async=True)
        if new != old:
            path.write_text(new, encoding="utf-8")
            n += 1
            print(path)
    print("changed", n, "files", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

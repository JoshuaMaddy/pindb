# Docstring audit tracker

Conventions follow the Google Python Style Guide (see
`.cursor/skills/python-preferences/SKILL.md`):

- **Module docstring** at the top of every file.
- **`Args` / `Returns` / `Raises`** on public helpers, ORM models (class-level
  summaries), and non-trivial functions.
- **Thin** docstrings on FastAPI route handlers and Pydantic field models unless
  behavior is surprising.

## Status (2026-04)

**`src/pindb/` is complete** for module-level documentation: every `*.py` file
opens with a module docstring. Core packages (`database/`, `auth`, `audit_events`,
`search/`, helpers) also have class/function docstrings where they add clarity.

Automated check (optional, for CI or pre-commit):

```powershell
uv run python scripts/verify_module_docstrings.py
```

## Other paths

| Area | Notes |
|------|--------|
| `scripts/` | `dump_db.py`, `migrate_data.py`, and `migrate_images.py` already had long module docs; `import_csv.py` documented. |
| `alembic/env.py` | Module docstring added. Migration files under `versions/` unchanged (historical). |
| `tests/` | Optional: add module docs to large fixtures when non-obvious. |

---

## Iteration log

| Iteration | Scope |
|-----------|--------|
| 0–1 | Tracker + package-root helpers (`markdown_utils`, `csrf`, `rate_limit`, …). |
| 2 | `audit_events`, `auth`, `config`, `lifespan`, `database/{__init__,base,session}`. |
| 3 | Full `database/` models and helpers, `models/`, `search/`, bulk module docs for all `routes/` and `templates/`, `import_csv.py`, `alembic/env.py`, `scripts/verify_module_docstrings.py`. |

---
name: python-preferences
description: Detailed guide to codebase Python style and preferences. Invoke when interacting with Python.
---

# Required Tooling

You can run all of these tools if installed globally, or, with `uvx run {tool}`.

## `uv`

Use `uv` for project setup, package management, and building. Use `uv` add to add dependencies to `pyproject.toml`.

## `ty`

Use `ty` for type checking.

## `ruff`

Use `ruff` for automatic formatting, linting, and import sorting.

## `pytest`

Use `pytest` for testing.

# Preferred libraries

## `rich` for printing, logging, tracing.

- Use a global `console` for printing and logging.
- `pprint` over `print`.
- `progress` for tracking processes.

## `polars` for DataFrames

Use `polars` for dataframes with the caveat that it can have runtime signaled dependencies, like `arrow` or `pandas`. Always consider if there are silent dependencies when using `polars`.

## `sqlalchemy` for database operations

Use `sqlalchemy` for connecting, reading, and writing to databases. If an ORM is needed, use declarative orm, fully typed.

## `pydantic` and `pydantic-settings` for strictly typed JSON and configuration

Strictly typed JSON parsing with `pydantic`, for both input and output.
Strictly typed singleton ENV parsing with `pydantic-settings`, for configuration from `.env` and or AWS parameter store, etc.

## `httpx` for modern requests

Use `httpx`, preferably async, for modern handling of requests.

## `tenacity` for retry logic

Use `tenacity` for sensitive, retryable calls like API requests.

## `FastAPI` and `uvicorn` for servers

Use `FastAPI` for building ASGI servers, with optional Jinja/Form packages. For deployment, use `uvicorn`. For development, use `fastapi run ...`.

# Documentation

Use Google Python Style Guide docstrings on all methods and classes, excluding highly structured and standardized methods/classes like `FastAPI` routes or `Pydantic` models.

```py
"""
Args:
    path (str): The path of the file to wrap
    field_storage (FileStorage): The :class:`FileStorage` instance to wrap
    temporary (bool): Whether or not to delete the file when the File
       instance is destructed

Returns:
    BufferedFileStorage: A buffered writable file descriptor
"""
```

Add documentation blocks to the top of all files and modules, summarizing the purpose of the file/module. Keep these in sync with changes.

# Code style

## Explicit types

All python code should be explicitly typed where possible and reasonable.
Bad untyped code:

```py
def artist_form(post_url, artist):
    artist_links = None
    if artist:
        artist_links = list(artist.links)
```

Good, explicitly typed at all levels:

```py
def artist_form(
    post_url: URL | str,
    artist: Artist | None = None,
) -> Element:
    artist_links: None | list[Link] = None
    if artist:
        artist_links: list[Link] = list(artist.links) # Note type reassignment
```

Example of 'unreasonable' typing is an external library enforcing loose typing - in which case narrow as best as possible with asserts/isinstance/if/else.
Another example of 'unreasonable' typing is excessively long `Literal["string"]` types.

## Avoid the use of `Any`, `object`

Never use the `Any` type or `object` unless it is the final and only option.

## Always use keywords when possible, unless intuitive from stdlib

When defining methods and calling methods, ALWAYS use keywords if possible.
Do not use positional parameters unless absolutely necessary, or, very obvious.
For example, if casting, eg `str(my_int)`, or if the method only has one parameter; `send_message("hello")`.

## One parameter per line

If a method definition or method call contains more than one parameter, place each parameter on its own line.

## Full variable names

Never use shortened variable names. Prefer full word variable names, even in inline comprehensions.

BAD: `[t.name for t in tags]`

GOOD: `[tag.name for tag in tags]`

## Always import absolutely

Import modules with absolute paths in all cases.

## Prefer `StrEnum` or `Enum` over literals

If using many `Literal`s, like `int` flags or `str` flags, prefer using an explicitly defined `Enum`.

## Prefer using `pydantic` first, then `dataclass`, then `TypedDict`.

When parsing or passing JSON or `dict`s, prefer interpreting as strictly defined `pydantic` models.
If not `pydantic`, then `DataClass`, then `TypedDict`.

## Use `pathlib` `Path`

Never hardcode paths, always use `pathlib.Path` for filesystem operations.

```py
from pathlib import Path
# Read relative positioned file
file = (Path(__file__).parent / "some_file.txt").resolve()
file.read_text()
```

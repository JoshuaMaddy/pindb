---
name: python-style
description: Detailed guide to codebase python style. Invoke when writing python.
---

# Python style preferences

## Explicit types

All python code should be explicitly typed where possible and reasonable.

For example, below is untyped code:

```py
def artist_form(post_url, artist):
    artist_links: = None
    if artist:
        artist_links = list(artist.links)
```

Instead, it should be explicitly typed at all levels:

```py
def artist_form(
    post_url: URL | str,
    artist: Artist | None = None,
) -> Element:
    artist_links: None | list[Link] = None
    if artist:
        artist_links: list[Link] = list(artist.links) # Note the type reassignment
```

An example of 'unreasonable' typing is when external libraries may enforce incredibly loose typing - in which case narrow as best as possible.
Another example of 'unreasonable' typing is excessively long `Literal["string"]` types.

## Always use keywords when possible, unless intuitive from stdlib.

When defining methods and calling methods, ALWAYS use keywords if possible.
Do not use positional parameters unless absolutely necessary, or, very obvious.
For example, if casting, eg `str(my_int)`, or if the method only has one parameter; `send_message("hello")`.

## Prefer StrEnum or Enum over literals

If using many `Literal`s, like `int` flags or `str` flags, prefer using an explicitly defined `Enum`.

## Prefer using Pydantic first, then DataClass, then TypedDict.

When parsing or passing JSON or `dict`s, prefer interpreting as strictly defined Pydantic models.
If not Pydantic, then DataClasses, then TypedDict.

## Additional simple rules:

1. If a method definition or method call contains more than one parameter, place each parameter on its own line.
2. Never use shortened variable names. Prefer full word variable names, even in inline comprehensions.

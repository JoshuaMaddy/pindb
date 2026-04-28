---
name: alpine-patterns
description: Detailed guide to AlpineJS usage patterns and pitfalls in PinDB. Invoke when writing or reviewing AlpineJS-driven routes, templates, or fragments.
---

# Alpine.js Patterns in PinDB

## Attribute Syntax in htpy

htpy offers three ways to write Alpine attributes, and each has the right context:

### 1. Keyword arguments (underscore → hyphen)

Works for any attribute whose name is a valid Python identifier after replacing `-` with `_`:

```python
div(x_data="{ open: false }", x_show="open", x_cloak=True)
```

Produces `x-data="{ open: false }" x-show="open" x-cloak`.

**Limitation:** Cannot express `@click`, `:class`, or event modifiers like `@click.self` — those are not valid Python identifiers.

### 2. Dict-key unpacking (arbitrary attribute names)

Required for `@` event handlers, `:` shorthand bindings, and Alpine modifiers:

```python
div(**{"@click": "open = true", ":class": "open ? 'active' : ''", "@click.self": "open = false"})
```

Dict keys are passed through as-is — no underscore substitution. Verified: htpy outputs them correctly.

### 3. `Markup(...)` escape hatch

Use when an Alpine template block is easier to write as a raw HTML string — typically when `<template x-for>` and `x-model` interact inside the same fragment:

```python
Markup(f"""<div x-data="{{ items: {json_data} }}">
    <template x-for="(item, i) in items" :key="i">
        <input x-model="items[i].name">
    </template>
</div>""")
```

See `__grades_input` and `__links_input` in `templates/create_and_edit/pin.py`. This is acceptable for isolated, self-contained snippets, but avoid it for components that need to interoperate with htpy elements around them.

---

## JSON Data Embedding

### The inline `x-data` quoting trap

The grades/links inputs embed JSON via `.replace('"', "'")` to avoid attribute quote conflicts:

```python
Markup(f'<div x-data="{{ items: {json.dumps(data).replace(\'"\', "\'")} }}">')
```

**This breaks for strings containing apostrophes** (e.g., `O'Brien`). Do not use this pattern for user data.

### Preferred approach: `Alpine.data()` + `<script>` tag

Register the component in a `<script>` tag using `Markup`. JSON goes inside `<script>` (no attribute escaping needed):

```python
from markupsafe import Markup

js = f"""
document.addEventListener('alpine:init', function () {{
    Alpine.data('myComponent', function () {{
        return {{
            rows: {json.dumps(rows).replace('</', '<\\/')},
            // ...
        }};
    }});
}});
"""

fragment[
    script[Markup(js)],
    div(**{"x-data": "myComponent"})[...],
]
```

Escape `</` → `<\/` in JSON to prevent the string `</script>` from terminating the tag early. `json.dumps()` handles all other escaping.

### `html_base(script_content=...)` for page-level JS

For large or reusable JS, load from an external file and pass to `html_base`:

```python
with open(Path(__file__).parent.parent / "js/my_script.js") as f:
    _SCRIPT = f.read()

html_base(..., script_content=_SCRIPT)
```

`html_base` wraps it in `script[Markup(content)]`. See `bulk/pin.py` and `create_and_edit/pin.py`.

---

## Initialization Timing

Alpine loads with `defer=True` in `<head>`. Execution order:

1. Inline `<script>` tags in `<body>` run as the parser reaches them.
2. After HTML is fully parsed, deferred scripts run — Alpine fires.
3. Alpine fires `alpine:init`, then processes the DOM.

**Consequence:** `document.addEventListener('alpine:init', ...)` registered in a body `<script>` will always fire before Alpine processes the page. This is the correct hook for `Alpine.data()` registration.

Do **not** use `window.onload` or `DOMContentLoaded` — Alpine may have already started by then.

---

## Scoping Patterns

### Inline scope for simple, one-off state

```python
div(x_data="{ open: false }")[
    button(**{"@click": "open = true"})["Open"],
    div(x_show="open")["Content"],
]
```

Use this for small, fully contained widgets like toggles and confirm modals. See `confirm_modal` in `templates/components/dialogs/confirm_modal.py`.

### Named component (`Alpine.data`) for complex or reusable state

```python
Alpine.data('dataTable_users', function () {
    return {
        rows: [...],
        get filteredRows() { ... },
        sort(col) { ... },
    };
});
```

Use this when the state object has computed properties, methods, or when the same logic might appear on multiple pages. The `data_table` component in `templates/components/display/data_table.py` is the canonical example.

**Unique naming:** When multiple instances of a named component can appear on one page, include a caller-supplied `table_id` in the name (`dataTable_{table_id}`) to avoid collisions.

---

## `<template x-for>` with htpy

`template` is a normal htpy element:

```python
from htpy import template as html_template

html_template(**{"x-for": "row in paginatedRows", ":key": "row.id"})[
    tr(...)[  # the row template; "row" is in scope here
        td(**{"x-text": "row.username"}),
    ]
]
```

**Rules:**

- `:key` goes on `<template>`, not on the inner element.
- The inner element uses `x-text`, `:class`, `:action` etc. via dict-key unpacking.
- htpy renders the inner element as static HTML; Alpine clones it at runtime.
- Lucide icons inside `x-for` rows will **not** be initialized by the `lucide.createIcons()` call at the bottom of `html_base` — that runs before Alpine processes the template. Avoid lucide icons inside `x-for` rows, or reinitialize manually via `htmx:afterSettle`.

---

## `x-cloak`

Use `x_cloak=True` on elements that should be invisible until Alpine initializes (prevents flash of un-styled content). Requires this CSS to be present:

```css
[x-cloak] {
  display: none !important;
}
```

See `confirm_modal` — the overlay div uses `x_cloak=True` so it doesn't flash on page load.

---

## Dynamic Form Actions

Alpine can set a `<form>`'s `action` attribute before submission:

```python
form(method="post", **{":action": "row.is_admin ? row.demote_url : row.promote_url"})[
    button(type="submit", **{"x-text": "row.is_admin ? 'Demote' : 'Promote'"}),
]
```

Include the URLs in the row data dict (computed server-side via `request.url_for()`). Do not construct route paths as string templates in Alpine — that couples the client to URL structure.

---

## Checklist

- Using `@` or `:` prefixes → use `**{"@click": "..."}` dict syntax, not kwargs
- Embedding JSON in `x-data` attribute → use `Alpine.data()` + `<script>` instead
- `</` in embedded JSON → escape to `<\/` before inserting into `<script>`
- Named Alpine components on the same page → include a unique ID in the component name
- Lucide icons inside `x-for` → avoid, or reinitialize after Alpine settles
- `x_cloak=True` on initially-hidden Alpine elements to prevent flash
- Form `:action` URLs → compute with `request.url_for()` server-side, embed in row data

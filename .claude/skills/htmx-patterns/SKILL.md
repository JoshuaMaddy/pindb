---
name: htmx-patterns
description: Detailed guide to HTMX usage patterns and pitfalls in PinDB. Invoke when writing or reviewing HTMX-driven routes, templates, or fragments.
---

# HTMX Patterns in PinDB

## Routes Reused from Multiple Contexts

Membership toggle endpoints are called from the pin detail page, the pin set edit search, and the pin set edit card list. Use `HX-Target` to return the right fragment for each:

```python
if request.headers.get("HX-Request"):
    hx_target = request.headers.get("HX-Target", "")
    if hx_target.startswith("pin-row-"):
        return HTMLResponse("")          # remove the card (outerHTML → nothing)
    elif hx_target.startswith("search-row-"):
        return HTMLResponse(str(search_result_row(...)))
    else:
        return HTMLResponse(str(set_row(...)))
```

Prefer `HX-Target` over `HX-Current-URL` (fragile to URL changes) or query params (couples template to route via string contract).

An **empty `HTMLResponse("")`** with `hx-swap="outerHTML"` removes the element from the DOM — use this for destructive removes rather than toggling state.

## Fragment ID Consistency

The most common silent bug: `hx-target="#search-row-42"` but the returned fragment has `id="set-row-5-42"`. HTMX performs the swap anyway, replacing the wrong element with mismatched content. Always verify the fragment function's root `id` matches the caller's `hx-target`.

## Public vs Private Fragment Functions

If a route imports a template helper to return it as a fragment, it must be public (no `_` prefix). Private helpers can't be imported across modules.

Fragment functions should live close to their page — the fragment for toggling a pin in the pin set edit flow lives in `templates/create_and_edit/pin_set.py`, not `templates/get/pin.py`.

## Two-Level Swap Pattern

Search containers use `innerHTML`; individual rows inside use `outerHTML`:

```python
input(hx_get=search_url, hx_trigger="input changed delay:300ms, search",
      hx_target="#pin-search-results", hx_swap="innerHTML")
div(id="pin-search-results")  # container — always present
```

Rows returned into the container have their own toggle buttons with `hx-swap="outerHTML"`. Don't mix these up — `innerHTML` on a toggle loses the element's own `id`; `outerHTML` on the container breaks future swaps into it.

## OOB Swaps and Third-Party JS (SortableJS)

Never OOB-replace a container that has JS bound to it — replacing the DOM node destroys the JS instance.

Instead, use targeted OOB operations that leave the container intact:

```python
div(hx_swap_oob="beforeend:#pin-list")[card(new_pin)]   # append without touching container
p(id="pin-list-empty", hx_swap_oob="delete")             # remove placeholder
h2(id="pin-list-count", hx_swap_oob="true")[f"Pins ({count})"]
```

**Always render JS-owned containers on initial page load, even when empty.** If `#pin-list` is conditionally omitted, `beforeend:#pin-list` will fail because the target doesn't exist. Render the container unconditionally; put the empty-state in a child with its own `id` so it can be OOB-deleted on first insert.

If destroying the container is unavoidable, reinitialize on `htmx:afterSettle` (fires after all OOB swaps complete):

```javascript
document.body.addEventListener("htmx:afterSettle", function () {
  var grid = document.getElementById("pin-list");
  if (grid && !Sortable.get(grid))
    Sortable.create(grid, {
      /* options */
    });
});
```

## Session Closed Before Fragment Rendered

htpy elements are **lazy** — they don't evaluate until stringified. If you build a fragment inside a `with session_maker()` block but return it before calling `str()`, the session is already closed when HTMX renders it, causing detached-instance errors. Either call `str(fragment(...))` inside the session block, or ensure all ORM attributes are accessed before the session closes.

## Checklist

- `hx-target` selector matches the `id` on the fragment's root element
- Route reused from two pages → dispatch on `HX-Target`
- Fragment helper is public (no `_` prefix) if a route imports it
- `hx-delete` paired with `@router.delete`, not `@router.post`
- JS-owned containers always rendered on page load, empty state is a child element
- Fragment stringified inside the session block

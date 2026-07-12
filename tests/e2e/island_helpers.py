"""Waiting for Svelte islands to finish mounting.

``page.wait_for_load_state("load")`` is not enough before clicking anything that
sits below an island. ``frontend/mount.ts`` mounts on the `load` event and
`import()`s each island's chunk, so the component renders a turn (or several,
under load) *after* Playwright considers the page loaded. A multi-select that
mounts grows from a bare ``<select>`` into a chip control and pushes everything
under it down the page.

That layout shift is invisible to ``click(force=True)``: `force` skips the
actionability checks, and the *stability* check is the one that would otherwise
wait for the element to stop moving. The click dispatches at coordinates the
target has already vacated, hits whatever moved into that spot, and the button
never sees it. Failure looks like "nothing happened" — no submit, no hint, no
navigation — and it only shows up under parallel load, which is what makes it a
maddening flake rather than an obvious bug.

So: wait for the islands, then click.
"""

from __future__ import annotations

from playwright.sync_api import Page

# A mount point is `<div data-island="…"><script type="application/json">…</script></div>`
# until its component renders into it, so "has a child that is not the props
# script" is the mounted signal. `mount.ts` also removes the element from its
# `mounted` map on failure — a component that throws on mount never renders a
# child, so this correctly keeps waiting rather than passing on a broken island.
_ISLANDS_MOUNTED = """() => {
  const roots = document.querySelectorAll('[data-island]');
  return [...roots].every((el) =>
    [...el.children].some((child) => child.tagName !== 'SCRIPT'),
  );
}"""


def wait_for_islands(page: Page, *, timeout: float = 15_000) -> None:
    """Block until every ``[data-island]`` on the page has rendered a component.

    No-op on pages without islands (``every`` over an empty list is true).
    """
    page.wait_for_function(_ISLANDS_MOUNTED, timeout=timeout)

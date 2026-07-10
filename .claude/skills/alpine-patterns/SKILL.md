---
name: alpine-patterns
description: RETIRED — Alpine.js was fully removed from PinDB (July 2026). Do not use Alpine. See CLAUDE.md "Svelte islands" for the replacement patterns.
---

# Alpine.js Patterns — RETIRED

Alpine.js has been fully removed from PinDB (July 2026 Svelte islands
migration). Do not introduce Alpine or `x-*` attributes.

Replacements:
- Complex interactive widgets → Svelte 5 islands (`frontend/`, mounted via
  `island(...)` from `templates/components/islands.py`). See CLAUDE.md.
- Pure show/hide disclosures (dropdowns, nav menu, panels) → the delegated
  `data-disclosure` / `data-disclosure-trigger` / `data-disclosure-panel`
  pattern handled by `templates/js/shell/pindb_shell.js` (toggle the `hidden`
  class; close on outside click / Escape; works inside htmx-swapped content
  with no re-init).
- Count labels fed by htmx swaps → `data-count-for` / `data-count-text` on the
  swapped fragment, applied by the shell on `htmx:afterSwap`.

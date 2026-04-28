---
name: theme-semantics
description: Use this skill when touching UI color classes in PinDB templates, JS-generated markup, or CSS.
---

# Theme Semantics

## Core Rules

1. Treat `darker -> main -> lighter -> lightest` as stacking order.
2. Use `*-hover` variants on interactive elements for hover/focus/active visuals.
3. Borders should use `border-lightest` or `border-accent` (and hover equivalents) for interactive and component-level chrome.
4. Structural borders (table/grid separators, section dividers, row rules) may use other semantic border colors when needed for hierarchy/legibility.
5. Use semantic error colors for destructive/error states: `error-dark`, `error-main`, and hover counterparts.
6. Use semantic pending colors (`pending-dark`, `pending-main`, and hover counterparts) for approvals-queue UX — banners, badges, and notes tied to “pending approval” or “pending edit”, same layering patterns as `error-*` but amber-based.
7. Do not introduce raw `pin-base-*`, custom mixes, or opacity-based new colors.

## Semantic Token Intent

- `darker`: deepest/background surfaces.
- `main`: default app shell/card surface.
- `lighter`: raised/intermediate surfaces.
- `lightest`: top-most subtle surfaces and muted text contexts.
- `base-text`: primary readable text.
- `accent`: links, CTAs, selected states, and emphasis.
- `error-dark`: dark destructive surface/border.
- `error-dark-hover`: hover state for `error-dark`.
- `error-main`: primary destructive text/icon/accent color.
- `error-main-hover`: hover state for `error-main`.
- `pending-dark` / `pending-dark-hover` / `pending-main` / `pending-main-hover`: queued-for-approval surfaces and accents (amber ramp; same roles as `error-*`).
- `darker-hover`, `main-hover`, `lighter-hover`, `lightest-hover`: interactive state versions of the same layer.
- `tag-*`: category palette tokens for tag/category chips and taxonomy visuals.

## Application Guidance

- **Backgrounds**
  - Choose by layer depth: page shell (`main`), nested panel (`lighter`), inset/chip (`lightest`).
  - For interactive containers (button rows, cards, pills), add `hover:bg-*-hover`.

- **Borders**
  - Neutral borders: `border-lightest`.
  - Emphasis/selection/action borders: `border-accent`.
  - Error borders/actions: `border-error-dark` or `border-error-main` depending on emphasis.
  - Pending-queue banners/badges (awaiting approval): `border-pending-dark` / `bg-pending-dark` with `text-pending-main`; hovers use `*-pending-*-hover`.
  - Interactive neutral borders should use `hover:border-lightest-hover`.
  - Interactive emphasized borders should use `hover:border-accent`.
  - Interactive error borders should use `hover:border-error-dark-hover` or `hover:border-error-main-hover`.
  - Structural separators (for example `border-b`, `border-t` in tables/lists) may use semantic non-lightest values when clarity requires it.

- **Text**
  - Default readable text: `text-base-text`.
  - Emphasis/action text: `text-accent`.
  - Error/destructive text: `text-error-main`.
  - Pending-queue text/accent: `text-pending-main` (and `*-hover` for interactive).
  - Muted/helper text: `text-lightest-hover`.
  - Interactive text should include `hover:text-*` and generally switch to `accent` for links/actions.

- **Tag categories**
  - Tag/category chips are a documented exception to the core neutral/accent ramp.
  - Use `tag-*` tokens from `templates/components/tag_branding.py` and `static/input.css`.
  - Do not remap tag-category colors to neutral/error semantics.

## Examples From Codebase

### 1) Layering + link hover (navbar)

```python
_LINK: str = "no-underline text-base-text hover:text-accent"
...
return nav(class_="px-2 py-1 bg-main relative z-[10]")[...]
...
class_="sm:hidden inline-flex ... border border-lightest ... text-base-text hover:bg-lighter-hover ..."
```

Source: `src/pindb/templates/components/navbar.py`

### 2) Interactive button with semantic hover

```python
button(
    type="submit",
    class_="... bg-main hover:bg-main-hover border border-lightest ... text-base-text ..."
)["Create Set"]
```

Source: `src/pindb/templates/create_and_edit/pin_set.py`

### 3) Border policy: accent for active, neutral for inactive

```python
_ACTIVE_CLASS: str = "px-3 py-1 rounded border border-accent text-accent ..."
_INACTIVE_CLASS: str = (
    "px-3 py-1 rounded border border-lightest text-lightest-hover ... "
    "hover:border-accent ..."
)
```

Source: `src/pindb/templates/list/base.py`

## Quick Checklist

- [ ] Layer order follows `darker -> main -> lighter -> lightest`.
- [ ] Interactive elements use `*-hover`.
- [ ] Borders use semantic families (`lightest`/`accent` by default; structural separators may use other semantic tones).
- [ ] Error/destructive states use `error-*` semantic tokens; pending-approval/edit surfaces use `pending-*`.
- [ ] No `pin-base-*` classes or ad-hoc color variants were introduced.

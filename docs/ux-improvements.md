# PinDB UX Improvements

Backlog of user-flow / UX findings from a code review of routes, templates, and JS.
Ranked by user pain. File refs point at the relevant code.

## Tier 1 — real holes, users get stuck

### 1. No password reset — DEFERRED (blocked on email)
`routes/auth/` has no forgot/reset flow. A password user who forgets their
password is locked out permanently — the only escape is OAuth, and only if a
provider was already linked. Build: forgot-password → emailed token → reset form.

**Blocked:** app has no email-sending infrastructure (only `contact_email` in
`config.py`). Deferred until email delivery is added.

### 2. Rejected edits vanish silently
Editor submits a pending edit; admin rejects (`approve.py` sets `rejected_at`).
The editor gets no notification and no reason — the work appears to evaporate.
Add a rejection-reason field and surface rejected items to their author with the why.

### 3. Search is not bookmarkable — DONE (facets/sort still open)
`/search/pin` was POST-only. Results couldn't be shared, bookmarked, or reached
with the back button, and there was no "no results" message.

**Done:** converted live search to `GET ?q=` with `hx-push-url`, so the query
lands in the URL. A bookmarked/shared `?q=` URL now renders results inline
server-side (no JS round-trip). Added a "No pins found for …" empty state.
**Still open:** facets (shop/artist/tag/acquisition) and sort options.

### 4. Pending edits hidden behind `?version=pending` — ALREADY DONE
Investigated: this is already implemented (commit `febe390`). On submit, the editor
is redirected to `?version=pending` with a "Changes submitted for review" toast
(`routes/edit/_pending_helpers.py:80`). A `pending_edit_banner`
(`templates/components/display/pending_edit_banner.py`) shows to any editor/admin on
both views and cross-links them: canonical view → "has a pending edit awaiting
approval · View pending →"; pending view → "Viewing pending edit · View canonical →".
No work needed. (Possible future polish: show pending indicator in list views, and
who/when submitted in the banner.)

## Tier 2 — friction, users finish but annoyed

### 5. No loading feedback on HTMX swaps — DONE
Pagination, sort, view-toggle, and search swapped the section silently — blank flash,
no spinner.

**Done:** added one global thin top progress bar
(`templates/js/forms/htmx_progress_bar.js`, mounted in `templates/base.py`) wired to
the HTMX request lifecycle on `document.body`. Covers every swap app-wide (lists,
pin search, detail panels) without per-control `hx-indicator`. Ref-counts concurrent
requests; 120ms show-delay avoids flashing on instant swaps; uses the theme-aware
`--color-accent`.

### 6. Validation fires only on submit (except name)
The name field has a live HTMX availability check; grades/acquisition/shops stay
silent until submit (`pin_creation.js:234`). Validate on blur and show inline hints,
not just a red ring.

### 7. Orphaned images on failed create
Images upload to storage *before* form validation. If the form fails, the bytes are
stranded (`routes/create/pin.py`). Validate first, or sweep orphans.

### 8. Sort has no direction indicator — DONE
"Newest"/"Oldest" buttons showed no arrow or active asc/desc cue, and the count was
a bare "N items".

**Done:** each sort option now carries a lucide chevron showing direction
(`chevron-up` = ascending, `chevron-down` = descending) — Name A→Z and Oldest are up,
Newest is down — shown on every option so direction is always legible; active option
also gets `aria-current`. Count replaced with "Showing X–Y of N" via
`_result_range_label` (`templates/list/base.py`). New chevron icons were pulled into
the tree-shaken lucide bundle (`node scripts/lucide/build-lucide.mjs`).

### 9. Destructive actions with no confirm — DONE (unlink)
Unlink OAuth provider had no confirmation; `confirm_modal.py` already existed.

**Done:** the Unlink button on the security page is now wrapped in `confirm_modal`
("Unlink {provider}? You will no longer be able to sign in with it…",
`templates/auth/security.py`). When it's the only remaining sign-in method the button
stays disabled with an explanatory tooltip (existing guard).
**Intentionally skipped:** confirm-on-admin-direct-edit — that's a routine save on the
common path, so a modal there would be friction, not a UX win.

### 10. Bulk import errors are hover-only
Row-level red border + `title=` attribute (`bulk_import.js:1206`). The user must
hover each row to learn what's wrong. Show inline per-field error text.

## Tier 3 — polish

- **Toast on silent success.** Profile settings and collection add return 204 with no
  feedback (`user/router.py:51`). Fire a toast.
- **Password strength meter** on signup/change — policy is shown only after a failure
  (`auth/router.py:197`).
- **Session management** — no view/revoke of active sessions on the security page.
  30-day sessions with no list.
- **Signup field-specific errors** — unified "username or email taken" (anti-enumeration,
  `router.py:206`) also blocks honest users. Tradeoff worth revisiting.
- **Alt text on pin card images** (`pin_preview_card.py`) — thumbnails lack `alt`.
- **Bulk import dead on mobile** — disabled below `md` with no fallback (`bulk/pin.py:97`).
- **Focus rings / skip-link** missing — keyboard nav is weak across grids.
- **Account delete** is immediate, with no email confirmation or grace window
  (`user/router.py:74`).

---

## Status

- [ ] #1 Password reset — **deferred** (needs email infra)
- [x] #3 Search as GET + no-results message — **done** (facets/sort still open)
- [x] #4 Pending edits visible — **already done** (banner + redirect, commit febe390)
- [x] #5 HTMX loading feedback — **done** (global progress bar)
- [x] #8 Sort direction chevrons + result range — **done**
- [x] #9 Confirm dialogs — **done** (unlink OAuth; admin-overwrite skipped by design)

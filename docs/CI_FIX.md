# CI Fix Tracking

## Status

- `docs/GITHUB_CI_ERRORS.md` contains **17 e2e failures**, but they do **not** behave like 17 independent product regressions.
- In the current workspace, I could **not reproduce** the failure cluster locally.
- The strongest current diagnosis is: **the GitHub CI log likely came from an earlier/unstable e2e run where long-lived Playwright contexts degraded over the course of the suite**, causing later HTMX/navigation-driven tests to fail in batches.

## Reproduction Log

### 1. Pending-edit integration checks

Command:

```powershell
uv run pytest tests/integration/test_pending_edits.py -q
```

Result:

- `6 passed in 13.28s`

Why this matters:

- The core server-side pending-edit workflow is healthy in isolation.
- This makes a deterministic backend regression in `routes/edit/shop.py`, `routes/approve.py`, or `database/pending_edit_utils.py` less likely.

### 2. Single failing e2e smoke test

Command:

```powershell
uv run pytest tests/e2e/test_flows.py -k "admin_creates_shop" -vv
```

Result:

- `1 passed`

Why this matters:

- The simplest "create shop via browser, then see it in the list" flow is currently working.

### 3. Targeted failing CI cluster under xdist

Command:

```powershell
uv run pytest -n 2 --dist loadfile tests/e2e/test_ui_content.py tests/e2e/test_pending_chain.py tests/e2e/test_concurrent.py tests/e2e/test_flows.py -k "admin_creates_shop or editor_pending_edit_approved_by_admin or pending_cascade_on_pin_approval or PendingQueueContent or PendingEditBanner or PendingEditReject or ThemeSwitcher or EditChainBuildup or EditChainNegative or PendingBannerLinksWork or InterleavedEdits or PendingBannerDisappearsAfterApprove" -vv
```

Result:

- `18 passed`

Why this matters:

- The exact failure family from the CI log now passes even under `xdist`.

### 4. Full e2e package

Command:

```powershell
uv run pytest tests/e2e -n 2 --dist loadfile -q
```

Result:

- `53 passed, 2 warnings`

Why this matters:

- The current workspace passes the whole e2e suite locally.
- This strongly suggests the CI log is either:
  - from a commit before the current e2e harness fixes landed, or
  - a Linux/GitHub Actions-only instability that is not reproducible on this Windows machine.

## Error Parsing And Diagnosis

## Bucket A: "Shop / pending item not visible"

Affected failures from `docs/GITHUB_CI_ERRORS.md`:

- `TestPendingQueueContent::test_editor_submission_appears_in_admin_queue_with_metadata`
- `TestPendingEditBanner::test_anonymous_user_does_not_see_pending_edit_banner`
- `TestPendingEditReject::test_admin_reject_removes_edit_from_queue_and_keeps_canonical`
- `test_admin_creates_shop`
- `test_editor_pending_edit_approved_by_admin`
- `test_pending_cascade_on_pin_approval`
- `TestPendingBannerDisappearsAfterApprove::test_banner_gone_once_admin_approves_chain`

Observed CI symptom:

- A shop was supposedly created or edited, but later pages could not find it in:
  - `/list/shops`
  - `/admin/pending`
  - shop detail banner state

Likely diagnosis:

- These are probably **secondary failures** caused by an earlier browser/e2e state problem, not distinct logic bugs in shop creation, approval, or visibility filtering.
- When the underlying HTMX submit or redirect does not fully land, every downstream assertion looks like "item missing".

Evidence:

- Current local runs pass both the simple create flow and the full e2e suite.
- The server-side pending-edit integration tests also pass.
- `tests/e2e/conftest.py` already contains an autouse cleanup fixture, `_close_pages_opened_during_test`, whose docstring explicitly says browser/page accumulation was the root cause of failures in this same family.

Current status:

- **Likely already fixed in current codebase**
- Not reproducible locally

## Bucket B: "Pending edit chain missing or stale"

Affected failures:

- `TestEditChainBuildup::test_two_editors_stack_edits_into_a_chain`
- `TestEditChainBuildup::test_admin_approve_edits_collapses_chain_in_order`
- `TestEditChainNegative::test_reject_edits_keeps_chain_invisible_but_preserved`
- `TestEditChainNegative::test_delete_edits_wipes_chain_and_canonical_unchanged`
- `TestInterleavedEdits::test_two_editors_submit_independent_edits_both_landed`
- `TestInterleavedEdits::test_admin_edit_during_pending_overwrites_canonical_only`
- `TestInterleavedEdits::test_admin_approves_after_admin_canonical_edit`
- `TestPendingBannerLinksWork::test_view_pending_link_navigates_to_pending_view`

Observed CI symptom:

- Pending edit count stayed at `0`, edit forms showed the canonical value instead of the pending snapshot, or the admin queue had no approve/reject/delete controls for the chain.

Likely diagnosis:

- Again, this looks like **the first pending-edit submit never actually landed during that CI run**.
- Once the first submit fails silently or the browser context is in a bad state, every later expectation in the chain is wrong:
  - no `PendingEdit` row
  - no pending snapshot
  - no admin queue row
  - no banner link

Evidence against a live backend bug:

- `tests/integration/test_pending_edits.py` passes.
- The xdist reproduction of the exact chain/concurrency tests passes.
- The current implementation in `routes/edit/shop.py`, `routes/approve.py`, and `database/pending_edit_utils.py` behaves correctly in local runs.

Current status:

- **Likely already fixed in current codebase**
- Not reproducible locally

## Bucket C: Theme switcher timeout

Affected failure:

- `TestThemeSwitcher::test_changing_theme_updates_html_class_without_reload`

Observed CI symptom:

- Playwright timed out waiting for the POST response to `/user/me/settings`.

Likely diagnosis:

- This does **not** currently look like a broken route.
- The route is minimal and deterministic: validate theme value, update the user row, return `204`.
- Because the test passes locally, this failure is more consistent with:
  - the browser context being degraded at that point in the suite, or
  - the expected `change`-driven HTMX request not firing during that CI run.

Current status:

- **No local repro**
- Treat as part of the broader e2e instability cluster unless GitHub Actions proves otherwise

## Most Likely Root Cause

At the moment, the best explanation is:

1. The CI log came from a run where the session-scoped Playwright contexts accumulated too much stale page state over time.
2. Once those contexts degraded, HTMX form submits and follow-up navigations started failing in bursts.
3. That produced many "missing item" and "missing pending edit" assertions that look like backend bugs but are really downstream symptoms.
4. The current repo already contains an e2e-harness mitigation for exactly this class of failure: closing newly opened pages after each test.

## Confidence Notes

High confidence:

- The current workspace does **not** have a reproducible pending-edit or shop-visibility regression.
- The server-side pending-edit logic is currently healthy.

Medium confidence:

- The historical CI failures were caused by e2e harness/browser-state instability rather than application logic.

Lower confidence / still unverified:

- Whether GitHub Actions on Linux still hits a platform-specific variant of the same problem.

## Next Verification Steps

- Re-run the GitHub Actions workflow on the current `main` commit.
- If it still fails, collect:
  - raw failing worker logs
  - Playwright screenshots/videos/traces
  - whether failures happen late in the worker lifetime again
- If the rerun is green, close this out as **historical CI failure cluster already addressed by the e2e cleanup changes**.

## CI Instrumentation Added

- Updated `.github/workflows/ci.yml` to make the next GitHub Actions run more diagnosable.
- The test job now:
  - enables uvicorn/e2e server logs with `E2E_SHOW_SERVER_LOGS=1`
  - raises server log verbosity to `info`
  - records Playwright traces on failure
  - records Playwright videos on failure
  - records Playwright screenshots on failure
  - writes `junit.xml`
  - uploads the `test-results` artifact unconditionally
- For diagnosis, xdist parallelism was temporarily reduced from `-n auto` to `-n 2` to lower worker-pressure noise and make failures easier to correlate.

## Artifact-Based Root Cause

- Examined GitHub run `24873363564` and job `72824508409`.
- The earliest failing test is still `TestPendingQueueContent::test_editor_submission_appears_in_admin_queue_with_metadata`, but the important signal is in the captured server logs before the assertions.
- The app repeatedly returned `404` for frontend assets under `/static`, including:
  - `/static/vendor/htmx.min.js`
  - `/static/vendor/alpine.min.js`
  - `/static/vendor/overtype.min.js`
  - `/static/vendor/notyf.min.js`
  - `/static/vendor/notyf.min.css`
  - `/static/vendor/tom-select.complete.min.js`
  - `/static/vendor/tom-select.default.min.css`
  - `/static/vendor/marked.min.js`
  - `/static/vendor/lucide.min.js`
  - `/static/main.css`
- This explains the failure pattern:
  - HTMX never loads, so create/edit form submissions do not perform the expected HTMX redirect flow.
  - Alpine/Tom Select/Overtype behavior is missing.
  - Theme-switch HTMX POST never fires.
  - The downstream tests then fail as "shop not found", "pending edit missing", or "button/link missing".

## Why It Passed Locally

- The missing files exist locally in this workspace.
- Verified locally:
  - `src/pindb/static/main.css` exists
  - `src/pindb/static/vendor/htmx.min.js` exists
  - `src/pindb/static/vendor/alpine.min.js` exists
- But these are generated assets and are gitignored:
  - `src/pindb/static/vendor/`
  - `src/pindb/static/main.css`
- So a fresh GitHub checkout does not have them unless CI builds them first.

## Fix Applied

- Updated `.github/workflows/ci.yml` to build frontend assets before running tests:
  - install Node 20
  - run `npm ci`
  - run `npm run build`
- This should make the same static assets available in CI that already exist locally.

## Working Conclusion

- No product-code fix is justified yet from this log alone.
- The actionable outcome today is:
  - document the failure cluster as likely e2e harness instability,
  - confirm with a fresh GitHub Actions rerun,
  - only reopen route-level debugging if CI still reproduces on the latest code.

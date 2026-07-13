---
name: deploy-prod
description: Deploy PinDB to production / update prod to main head via the pindb SSH host. Invoke when asked to deploy, ship, release, update prod, roll out to production, or report on a prod deploy's health.
---

# Deploying PinDB to Production

Prod runs on a single VPS reachable over SSH as host **`pindb`** (`ssh pindb`). Repo lives at
**`/root/pindb`**. Deploys are zero-downtime blue/green via Caddy. Everything below runs on the
remote — prefix each command with `ssh pindb '...'` or open one session and stay in `/root/pindb`.

## The load-bearing fact: app code ships as a prebuilt image, NOT from the checked-out repo

`scripts/deploy.sh` runs `docker compose pull` of **`ghcr.io/joshuamaddy/pindb:latest`** — it does
**not** build locally. That image is built and pushed by the **`.github/workflows/release.yml`**
("Release") workflow on every push to `main`.

Consequences:
- **App/Python/JS/template changes reach prod only after the Release workflow finishes** and pushes
  `:latest`. Running `deploy.sh` before CI is done deploys the *previous* image.
- `git pull` on prod updates only host-side files: `docker-compose.yaml`, `scripts/`, the Caddyfile,
  Alembic migration files (used by the one-shot `migrate` service, which builds from `file:///app`
  inside the image). It does **not** update the running app code.

So "update prod to main head" = **(1)** confirm CI pushed the new `:latest`, **(2)** `git pull` on
prod for infra/migration files, **(3)** `./scripts/deploy.sh`, **(4)** verify health.

## Procedure

### 1. Confirm CI has pushed the new image
Push/merge to `main` triggers Release. Do not deploy until it's green.
```bash
gh run list --workflow=release.yml --branch main --limit 3      # from local checkout
```
Wait for the run matching the target commit to be `completed / success`.

### 2. Update prod repo (infra + migration files)
```bash
ssh pindb 'cd /root/pindb; git fetch origin --quiet; git status -sb'
```
- Prod repo often carries a harmless local diff: **`scripts/deploy.sh` mode 644→755** (exec bit) and
  untracked cruft (`images/`, `logs/`, `overwrite.yaml` — an old single-`app` compose leftover, not
  used by blue/green). None of these block a fast-forward.
- Check incoming range before pulling; make sure nothing local would be clobbered:
```bash
ssh pindb 'cd /root/pindb; git log --oneline HEAD..origin/main; git diff --stat HEAD..origin/main'
ssh pindb 'cd /root/pindb; git pull --ff-only origin main'
```
If FF fails because of a real local edit, inspect (`git diff <file>`) before deciding — do not blow
away host config.

### 3. Deploy
```bash
ssh pindb 'cd /root/pindb; ./scripts/deploy.sh 2>&1'
```
Use a long timeout (image pull can be minutes). What it does (`scripts/deploy.sh`):
1. Reads live color from `.deploy-active-color` (gitignored, host-local; default `blue`).
2. Pulls `:latest` for both colors + `migrate` + `scheduler`.
3. Runs migrations once via the one-shot `migrate` service (`compose run --rm migrate`).
4. Brings up the **idle** color alongside live, waits ≤90s for `/healthz` healthy.
5. Smoke-tests `http://localhost:8000/healthz` through the proxy.
6. Stops+removes the old color, recreates `scheduler` on the new image, ensures `proxy` up.
7. `docker image prune -f` + `docker builder prune -f` — every deploy pulls a new image layer set
   and leaves the previous one dangling; nothing else on the host cleans that up. Only touches
   dangling images and build cache, never a running container, a tagged image still in use, or a
   volume.
8. Writes the new color to `.deploy-active-color`.

**Abort behavior is safe:** if the new color never goes healthy, deploy.sh stops the new color and
leaves the old one live (exits 1). No downtime, no manual rollback needed — investigate logs and
retry.

### 4. Verify healthy deploy (always report this)
```bash
ssh pindb 'cd /root/pindb;
  echo "active: $(cat .deploy-active-color)";
  curl -fsS -m5 localhost:8000/healthz && echo;
  docker compose ps --format "table {{.Name}}\t{{.Service}}\t{{.Status}}"'
```
Healthy result:
- `.deploy-active-color` flipped to the new color.
- `/healthz` → `ok`.
- `app_<color>` = `Up (healthy)`. The freshly recreated `scheduler` shows `health: starting` for a
  few seconds — normal, not a failure. `postgres`, `meilisearch`, `proxy` stay up across deploys.

To pin exactly what shipped, compare the running image digest to CI, or check the deployed git sha
if surfaced by the app version/footer.

## Gotchas
- **Disk fills up from dangling images if deploy.sh's prune step is ever skipped/removed.** Each
  deploy pulls a new `ghcr.io/joshuamaddy/pindb:latest` layer set; the old one becomes dangling and
  nothing else on the host cleans it up. Hit 100% full once (2026-07-12), which surfaced as pin/
  display image uploads 500ing with `OSError: [Errno 28] No space left on device` in
  `file_handler.py::save` — nothing wrong with the upload code, the disk was just full. Check with
  `ssh pindb 'df -h /; docker system df'`; fix with `docker image prune -f && docker builder prune -f`
  (now automated as the last step of `deploy.sh`).
- **Deploying stale image:** ran `deploy.sh` before Release finished → `:latest` is old. Re-run once
  CI completes.
- **Only one color runs normally**; both are up for ~10–30s mid-swap. During that window old + new
  code hit the same DB, so migrations must be forward- and backward-compatible (see CLAUDE.md
  "Migration discipline"). Never ship a same-release `DROP COLUMN` / `NOT NULL` on a column old code
  can leave null.
- **Scheduler is separate:** `ENABLE_SCHEDULER=true` only on the `scheduler` container (1 replica);

  web containers set it false so cron/Meili-sync jobs never double-fire.
- **Bootstrap vs deploy:** first-time / after `compose down` use `./scripts/bootstrap.sh` (brings up
  postgres+meili+active color+scheduler+proxy, ~5–15s of NPM 502s). Steady-state daily use is
  `deploy.sh`.
- **Rollback:** re-point `:latest` (or set `IMAGE_TAG` to a prior `sha-<hash>` tag that CI published)
  and re-run `deploy.sh`; blue/green swaps back into the previous image.
```bash
ssh pindb 'cd /root/pindb; IMAGE_TAG=sha-<goodsha> ./scripts/deploy.sh'
```

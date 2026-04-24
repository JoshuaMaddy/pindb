#!/usr/bin/env bash
# First-time setup for the blue/green deploy stack.
#
# Idempotent: safe to re-run if a previous bootstrap failed partway through.
# After this finishes, every subsequent deploy is `./scripts/deploy.sh`.
#
# Causes ~5–15s of NPM 502s ONCE — when the legacy single `app` container
# releases host:8000 and the new `proxy` container claims it. After that the
# stack is zero-downtime. Containers all use `restart: unless-stopped`, so the
# Docker daemon brings them back automatically after host reboots.
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT="${COMPOSE_PROJECT_NAME:-pindb}"
STATE_FILE=".deploy-active-color"

echo "==> Checking prerequisites"
command -v docker >/dev/null || { echo "!! docker not installed" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "!! docker compose v2 required" >&2; exit 1; }
[ -f .env ] || { echo "!! .env missing — copy .env.example and fill in" >&2; exit 1; }

# Validate required vars exist (presence only, not correctness).
missing=()
for var in POSTGRES_PASSWORD MEILISEARCH_KEY; do
  grep -qE "^${var}=" .env || missing+=("$var")
done
if [ ${#missing[@]} -gt 0 ]; then
  echo "!! .env missing required vars: ${missing[*]}" >&2
  exit 1
fi

# Verify Docker daemon is set to start on boot — load-bearing for restart hardening.
if command -v systemctl >/dev/null 2>&1; then
  if ! systemctl is-enabled --quiet docker 2>/dev/null; then
    echo "!! WARNING: 'systemctl is-enabled docker' returned non-enabled."
    echo "   Run: sudo systemctl enable docker"
    echo "   Without this, containers won't start on host reboot."
  fi
fi

echo "==> Initial active color"
if [ -f "$STATE_FILE" ]; then
  ACTIVE=$(cat "$STATE_FILE")
  echo "   Existing state: $ACTIVE"
else
  ACTIVE=blue
  echo "$ACTIVE" > "$STATE_FILE"
  echo "   Wrote $STATE_FILE = $ACTIVE"
fi

echo "==> Building image"
docker compose --profile blue --profile green build app_blue app_green

echo "==> Releasing host:8000 from any pre-existing single-app container"
# These no-op if the legacy `app` service was never deployed on this host.
docker compose stop app 2>/dev/null || true
docker compose rm -f app 2>/dev/null || true

echo "==> Starting infra (postgres + meilisearch)"
docker compose up -d --remove-orphans postgres meilisearch

echo "==> Waiting for postgres + meilisearch to be healthy"
for svc in postgres meilisearch; do
  cid=$(docker compose ps -q "$svc")
  for _ in $(seq 1 30); do
    state=$(docker inspect --format='{{.State.Health.Status}}' "$cid" 2>/dev/null || echo "starting")
    [ "$state" = "healthy" ] && break
    sleep 2
  done
  [ "$state" = "healthy" ] || { echo "!! $svc never went healthy" >&2; exit 1; }
done

echo "==> Running migrations"
docker compose --profile migrate run --rm migrate

echo "==> Starting app_$ACTIVE"
docker compose --profile "$ACTIVE" up -d "app_$ACTIVE"

echo "==> Waiting for app_$ACTIVE to be healthy"
CONTAINER="${PROJECT}-app_${ACTIVE}-1"
state="starting"
for _ in $(seq 1 45); do
  state=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null || echo "starting")
  [ "$state" = "healthy" ] && break
  sleep 2
done
if [ "$state" != "healthy" ]; then
  echo "!! app_$ACTIVE never went healthy ($state)" >&2
  echo "   Logs: docker logs $CONTAINER" >&2
  exit 1
fi

echo "==> Starting scheduler + proxy (proxy claims host:8000 — brief 502s through NPM here)"
docker compose up -d scheduler proxy

echo "==> Smoke test"
for _ in $(seq 1 15); do
  if curl -fsS http://localhost:8000/healthz >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -fsS http://localhost:8000/healthz >/dev/null

echo "==> Bootstrap complete. Active color: $ACTIVE"
echo "   Future deploys: ./scripts/deploy.sh"
echo "   Manual recovery (e.g. after pruning): ./scripts/start.sh"

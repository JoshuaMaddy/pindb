#!/usr/bin/env bash
# Zero-downtime blue/green deploy.
#
# Builds a new image, runs migrations once, brings up the idle color alongside
# the live one, waits for it to pass /healthz, then stops the old color.
# Caddy load-balances across both upstreams and routes only to the healthy one,
# so traffic never hits a draining or booting container.
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT="${COMPOSE_PROJECT_NAME:-pindb}"
STATE_FILE=".deploy-active-color"

ACTIVE=$(cat "$STATE_FILE" 2>/dev/null || echo "blue")
if [ "$ACTIVE" = "blue" ]; then NEXT=green; else NEXT=blue; fi

echo "==> Active: $ACTIVE   Next: $NEXT"

echo "==> Pulling image from ghcr.io (tag: ${IMAGE_TAG:-latest})"
docker compose --profile blue --profile green --profile migrate pull app_blue app_green migrate scheduler

echo "==> Running migrations"
docker compose --profile migrate run --rm migrate

echo "==> Starting $NEXT alongside $ACTIVE"
docker compose --profile blue --profile green up -d --no-deps --force-recreate "app_$NEXT"

echo "==> Waiting for $NEXT to be healthy"
CONTAINER="${PROJECT}-app_${NEXT}-1"
health="starting"
for _ in $(seq 1 45); do
  status=$(docker inspect --format='{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo "missing")
  health=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null || echo "starting")
  if [ "$status" = "exited" ] || [ "$status" = "dead" ]; then
    echo "!! $NEXT container $status; logs:" >&2
    docker logs --tail 80 "$CONTAINER" >&2 || true
    exit 1
  fi
  if [ "$health" = "healthy" ]; then break; fi
  sleep 2
done
if [ "$health" != "healthy" ]; then
  echo "!! $NEXT never went healthy (status=$status health=$health); leaving $ACTIVE live and aborting" >&2
  docker logs --tail 80 "$CONTAINER" >&2 || true
  docker compose --profile "$NEXT" stop "app_$NEXT"
  exit 1
fi

echo "==> Smoke test via proxy"
curl -fsS http://localhost:8000/healthz >/dev/null

echo "==> Stopping $ACTIVE"
docker compose --profile "$ACTIVE" stop "app_$ACTIVE"
docker compose --profile "$ACTIVE" rm -f "app_$ACTIVE"

echo "==> Restarting scheduler on new image"
docker compose up -d --no-deps scheduler

echo "==> Ensuring proxy is up"
docker compose up -d --no-deps proxy

echo "$NEXT" > "$STATE_FILE"
echo "==> Deploy complete; $NEXT now live"

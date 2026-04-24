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

echo "==> Building image"
docker compose --profile blue --profile green build app_blue app_green

echo "==> Running migrations"
docker compose --profile migrate run --rm migrate

echo "==> Starting $NEXT alongside $ACTIVE"
docker compose --profile "$NEXT" up -d "app_$NEXT"

echo "==> Waiting for $NEXT to be healthy"
CONTAINER="${PROJECT}-app_${NEXT}-1"
state="starting"
for _ in $(seq 1 30); do
  state=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null || echo "starting")
  if [ "$state" = "healthy" ]; then break; fi
  sleep 2
done
if [ "$state" != "healthy" ]; then
  echo "!! $NEXT never went healthy ($state); leaving $ACTIVE live and aborting" >&2
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

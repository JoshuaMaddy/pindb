#!/usr/bin/env bash
# Bring the stack up using the currently-active color from .deploy-active-color.
#
# Normally unnecessary — `restart: unless-stopped` causes the Docker daemon to
# restart all stack containers automatically after a host reboot. Use this when
# containers were manually pruned, after `docker compose down`, or as the
# command in a systemd unit if you want explicit control over startup.
set -euo pipefail
cd "$(dirname "$0")/.."

STATE_FILE=".deploy-active-color"
ACTIVE=$(cat "$STATE_FILE" 2>/dev/null || echo "blue")

if [ "$ACTIVE" = "blue" ]; then INACTIVE=green; else INACTIVE=blue; fi

echo "==> Bringing up stack with active color: $ACTIVE"
docker compose up -d postgres meilisearch
docker compose --profile "$ACTIVE" up -d "app_$ACTIVE"
docker compose up -d scheduler proxy

echo "==> Stopping inactive color: $INACTIVE (if running)"
docker compose --profile "$INACTIVE" stop "app_$INACTIVE" 2>/dev/null || true
docker compose --profile "$INACTIVE" rm -f "app_$INACTIVE" 2>/dev/null || true

echo "==> Up. Verify: curl -fsS http://localhost:8000/healthz"

#!/usr/bin/env bash
set -e

# Install JS deps if missing.
if [ ! -d node_modules ]; then
    echo "Installing npm dependencies..."
    npm ci
fi

# Build CSS + vendor assets once so first page load works before css:watch kicks in.
npm run build

docker compose -f docker-compose.dev.yaml up -d
fastapi dev ./src/pindb/ --host 0.0.0.0

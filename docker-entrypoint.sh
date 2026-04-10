#!/bin/bash
set -e

echo "Running database migrations..."
uv run alembic upgrade head

echo "Starting server..."
exec uv run fastapi run ./src/pindb/ --host 0.0.0.0 --port 8000

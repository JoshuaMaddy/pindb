#!/bin/bash
set -e

exec uv run uvicorn pindb:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'

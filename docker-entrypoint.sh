#!/bin/bash
set -e

# FORWARDED_ALLOW_IPS decides whose X-Forwarded-For uvicorn believes. The
# rate limiter keys on the resulting client IP, so with the default '*' any
# client can spoof the header and mint itself a fresh login-attempt budget per
# request. Pin it to the proxy's address on the compose network to close that.
exec /app/.venv/bin/python -m uvicorn pindb:app \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}"

#!/bin/sh
# Runs database migrations (unless RUN_MIGRATIONS=0), then the API.
# One worker: the login rate limiter is in-process. Scale by adding containers only
# after moving rate limiting to a shared store.
set -eu

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  alembic upgrade head
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers 1 \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
  --no-server-header

#!/bin/sh
set -eu

if [ -z "${MIGRATION_DATABASE_URL:-}" ]; then
  echo "MIGRATION_DATABASE_URL is required" >&2
  exit 1
fi
if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

alembic -c /app/apps/api/alembic.ini upgrade head
exec uvicorn synapse_api.main:app --host 0.0.0.0 --port 8000

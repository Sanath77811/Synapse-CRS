#!/bin/sh
# Start the API only. Migrations run in a separate one-shot process so this
# process never receives the migration role's connection string.
set -eu

if [ -n "${MIGRATION_DATABASE_URL+x}" ]; then
  echo "MIGRATION_DATABASE_URL must not be set for the API process" >&2
  exit 1
fi
if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

exec uvicorn synapse_api.main:app --host 0.0.0.0 --port 8000

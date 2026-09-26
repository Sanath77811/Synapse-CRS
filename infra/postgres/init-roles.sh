#!/bin/sh
# Create the application role before migrations grant it table privileges.
# The official Postgres image runs this once, on an empty data volume.
set -eu

case "${POSTGRES_DB}" in
  *[!A-Za-z0-9_]*)
    echo "POSTGRES_DB contains unsupported characters" >&2
    exit 1
    ;;
esac

case "${SYNAPSE_APP_PASSWORD}" in
  *[!A-Za-z0-9_-]*)
    echo "SYNAPSE_APP_PASSWORD contains unsupported characters" >&2
    exit 1
    ;;
esac

if [ "${#SYNAPSE_APP_PASSWORD}" -lt 16 ]; then
  echo "SYNAPSE_APP_PASSWORD must be at least 16 characters" >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOF
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'synapse_app') THEN
    CREATE ROLE synapse_app LOGIN PASSWORD '${SYNAPSE_APP_PASSWORD}';
  END IF;
END
\$\$;
GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO synapse_app;
EOF

-- Run as the managed PostgreSQL owner BEFORE Alembic.
-- Replace CHANGE_ME_APP_PASSWORD with a 16–128 character [A-Za-z0-9_-] secret.
-- Replace YOUR_DATABASE_NAME with the actual database name.
-- Do not commit the filled-in password.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'synapse_app') THEN
    CREATE ROLE synapse_app LOGIN PASSWORD 'CHANGE_ME_APP_PASSWORD';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE YOUR_DATABASE_NAME TO synapse_app;
GRANT USAGE ON SCHEMA public TO synapse_app;

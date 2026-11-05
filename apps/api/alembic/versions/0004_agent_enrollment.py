"""Register agents against authorized targets.

Revision ID: 0004_agent_enrollment
Revises: 0003_telemetry_events
Create Date: 2026-11-04

synapse_app may SELECT and INSERT agents, and UPDATE only enrollment
lifecycle columns. It cannot change target_id or delete agents.
"""

from alembic import op

revision = "0004_agent_enrollment"
down_revision = "0003_telemetry_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE agents (
            id UUID PRIMARY KEY,
            target_id UUID NOT NULL REFERENCES targets (id),
            public_key_hex TEXT NOT NULL UNIQUE CHECK (public_key_hex ~ '^[0-9a-f]{64}$'),
            public_key_fingerprint TEXT NOT NULL CHECK (
                public_key_fingerprint ~ '^sha256:[0-9a-f]{64}$'
            ),
            key_generation INTEGER NOT NULL CHECK (key_generation >= 1),
            status TEXT NOT NULL CHECK (status IN ('active', 'revoked')),
            enrolled_at TIMESTAMPTZ NOT NULL,
            enrolled_by TEXT NOT NULL CHECK (char_length(enrolled_by) BETWEEN 1 AND 200),
            revoked_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ NOT NULL,
            CHECK (
                (status = 'active' AND revoked_at IS NULL)
                OR (status = 'revoked' AND revoked_at IS NOT NULL)
            )
        )
        """
    )
    op.execute("CREATE INDEX agents_target_id_idx ON agents (target_id)")
    op.execute("CREATE INDEX agents_status_idx ON agents (status)")
    op.execute("CREATE INDEX agents_fingerprint_idx ON agents (public_key_fingerprint)")
    op.execute(
        """
        CREATE FUNCTION synapse_enforce_agent_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id THEN
                RAISE EXCEPTION 'agent id is immutable' USING ERRCODE = '55000';
            END IF;
            IF NEW.target_id IS DISTINCT FROM OLD.target_id THEN
                RAISE EXCEPTION 'agent target binding is immutable' USING ERRCODE = '55000';
            END IF;
            IF NEW.enrolled_at IS DISTINCT FROM OLD.enrolled_at
               OR NEW.enrolled_by IS DISTINCT FROM OLD.enrolled_by THEN
                RAISE EXCEPTION 'agent enrollment metadata is immutable' USING ERRCODE = '55000';
            END IF;
            IF NEW.status IS DISTINCT FROM OLD.status
               AND (
                    OLD.status IS DISTINCT FROM 'active'
                    OR NEW.status IS DISTINCT FROM 'revoked'
               )
            THEN
                RAISE EXCEPTION 'agent revocation is one-way' USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER agents_enforce_update
        BEFORE UPDATE ON agents
        FOR EACH ROW
        EXECUTE FUNCTION synapse_enforce_agent_update()
        """
    )
    op.execute(
        """
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT c.conname INTO constraint_name
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = 'telemetry_events'
              AND c.contype = 'c'
              AND pg_get_constraintdef(c.oid) ILIKE '%identity_status%'
            LIMIT 1;
            IF constraint_name IS NULL THEN
                RAISE EXCEPTION 'identity_status check constraint was not found'
                    USING ERRCODE = '42704';
            END IF;
            EXECUTE format(
                'ALTER TABLE telemetry_events DROP CONSTRAINT %I',
                constraint_name
            );
        END
        $$
        """
    )
    op.execute(
        """
        ALTER TABLE telemetry_events
            ADD CONSTRAINT telemetry_events_identity_status_check
            CHECK (identity_status IN ('unverified', 'enrolled'))
        """
    )
    op.execute(
        """
        CREATE FUNCTION synapse_enforce_telemetry_identity()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            agent_status TEXT;
            agent_target UUID;
            agent_key TEXT;
        BEGIN
            IF NEW.identity_status = 'unverified' THEN
                RETURN NEW;
            END IF;
            SELECT status, target_id, public_key_hex
              INTO agent_status, agent_target, agent_key
              FROM agents
             WHERE id = NEW.agent_id;
            IF NOT FOUND
               OR agent_status IS DISTINCT FROM 'active'
               OR agent_target IS DISTINCT FROM NEW.target_id
               OR agent_key IS DISTINCT FROM NEW.public_key_hex
            THEN
                RAISE EXCEPTION 'telemetry identity is not enrolled' USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER telemetry_events_enforce_identity
        BEFORE INSERT ON telemetry_events
        FOR EACH ROW
        EXECUTE FUNCTION synapse_enforce_telemetry_identity()
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'synapse_app') THEN
                RAISE EXCEPTION 'synapse_app role must exist before privileges are granted'
                    USING ERRCODE = '42501';
            END IF;
            GRANT SELECT, INSERT ON agents TO synapse_app;
            GRANT UPDATE (
                public_key_hex,
                public_key_fingerprint,
                key_generation,
                status,
                revoked_at,
                updated_at
            ) ON agents TO synapse_app;
        END
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS telemetry_events_enforce_identity ON telemetry_events")
    op.execute("DROP FUNCTION IF EXISTS synapse_enforce_telemetry_identity()")
    op.execute(
        """
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT c.conname INTO constraint_name
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = 'telemetry_events'
              AND c.contype = 'c'
              AND pg_get_constraintdef(c.oid) ILIKE '%identity_status%'
            LIMIT 1;
            IF constraint_name IS NULL THEN
                RAISE EXCEPTION 'identity_status check constraint was not found'
                    USING ERRCODE = '42704';
            END IF;
            EXECUTE format(
                'ALTER TABLE telemetry_events DROP CONSTRAINT %I',
                constraint_name
            );
        END
        $$
        """
    )
    op.execute(
        """
        ALTER TABLE telemetry_events
            ADD CONSTRAINT telemetry_events_identity_status_check
            CHECK (identity_status = 'unverified')
        """
    )
    op.execute("DROP TRIGGER IF EXISTS agents_enforce_update ON agents")
    op.execute("DROP TABLE IF EXISTS agents")
    op.execute("DROP FUNCTION IF EXISTS synapse_enforce_agent_update()")

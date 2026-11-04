"""Append-only telemetry evidence store.

Revision ID: 0003_telemetry_events
Revises: 0002_enforce_state
Create Date: 2026-11-04

synapse_app may SELECT and INSERT. It cannot UPDATE or DELETE evidence.
There is no foreign key to targets: a signed event may name a target that
is not registered. Enrollment is not implemented.
"""

from alembic import op

revision = "0003_telemetry_events"
down_revision = "0002_enforce_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE telemetry_events (
            id UUID PRIMARY KEY,
            event_id UUID NOT NULL,
            target_id UUID NOT NULL,
            agent_id UUID NOT NULL,
            boot_id UUID NOT NULL,
            event_type TEXT NOT NULL CHECK (
                event_type IN (
                    'process_started',
                    'process_exited',
                    'network_connection_observed'
                )
            ),
            sequence BIGINT NOT NULL CHECK (
                sequence >= 1 AND sequence <= 9223372036854775807
            ),
            observed_at TIMESTAMPTZ NOT NULL,
            schema_version TEXT NOT NULL CHECK (schema_version = '1.0.0'),
            envelope JSONB NOT NULL CHECK (jsonb_typeof(envelope) = 'object'),
            signature TEXT NOT NULL CHECK (
                char_length(signature) = 88
                AND signature ~ '^[A-Za-z0-9+/]{86}==$'
            ),
            public_key_hex TEXT NOT NULL CHECK (public_key_hex ~ '^[0-9a-f]{64}$'),
            public_key_fingerprint TEXT NOT NULL CHECK (
                public_key_fingerprint ~ '^sha256:[0-9a-f]{64}$'
            ),
            signature_verified BOOLEAN NOT NULL CHECK (signature_verified IS TRUE),
            identity_status TEXT NOT NULL CHECK (identity_status = 'unverified'),
            received_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT telemetry_events_event_id_key UNIQUE (event_id),
            CONSTRAINT telemetry_events_agent_boot_sequence_key
                UNIQUE (agent_id, boot_id, sequence)
        )
        """
    )
    op.execute("CREATE INDEX telemetry_events_target_id_idx ON telemetry_events (target_id)")
    op.execute("CREATE INDEX telemetry_events_agent_id_idx ON telemetry_events (agent_id)")
    op.execute("CREATE INDEX telemetry_events_event_type_idx ON telemetry_events (event_type)")
    op.execute(
        "CREATE INDEX telemetry_events_observed_at_idx ON telemetry_events (observed_at, event_id)"
    )
    op.execute(
        """
        CREATE FUNCTION synapse_reject_telemetry_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'telemetry_events are append-only'
                USING ERRCODE = '55000';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER telemetry_events_append_only
        BEFORE UPDATE OR DELETE ON telemetry_events
        FOR EACH ROW
        EXECUTE FUNCTION synapse_reject_telemetry_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER telemetry_events_no_truncate
        BEFORE TRUNCATE ON telemetry_events
        FOR EACH STATEMENT
        EXECUTE FUNCTION synapse_reject_telemetry_mutation()
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
            GRANT SELECT, INSERT ON telemetry_events TO synapse_app;
        END
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS telemetry_events_no_truncate ON telemetry_events")
    op.execute("DROP TRIGGER IF EXISTS telemetry_events_append_only ON telemetry_events")
    op.execute("DROP TABLE IF EXISTS telemetry_events")
    op.execute("DROP FUNCTION IF EXISTS synapse_reject_telemetry_mutation()")

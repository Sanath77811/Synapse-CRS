"""Initial v0.1 schema: targets, cases, and an append-only audit chain.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-26
"""

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

GENESIS_HASH = "0" * 64


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE targets (
            id UUID PRIMARY KEY,
            name TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 200),
            owner TEXT NOT NULL CHECK (char_length(owner) BETWEEN 1 AND 200),
            scope JSONB NOT NULL CHECK (jsonb_typeof(scope) = 'object'),
            authorization_status TEXT NOT NULL
                CHECK (authorization_status IN ('active', 'revoked')),
            authorization_expiry TIMESTAMPTZ NOT NULL,
            allowed_capabilities JSONB NOT NULL
                CHECK (jsonb_typeof(allowed_capabilities) = 'array'),
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE cases (
            id UUID PRIMARY KEY,
            target_id UUID NOT NULL REFERENCES targets (id),
            state TEXT NOT NULL CHECK (
                state IN (
                    'AUTHORIZED_TARGET',
                    'OBSERVATION',
                    'EVIDENCE',
                    'HYPOTHESIS',
                    'VERIFICATION',
                    'APPROVAL',
                    'ACTION',
                    'VALIDATION',
                    'ROLLBACK',
                    'SEALED_AUDIT'
                )
            ),
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            created_by TEXT NOT NULL CHECK (char_length(created_by) BETWEEN 1 AND 200)
        )
        """
    )
    op.execute("CREATE INDEX cases_target_id_idx ON cases (target_id)")
    op.execute(
        """
        CREATE TABLE case_transitions (
            id UUID PRIMARY KEY,
            case_id UUID NOT NULL REFERENCES cases (id),
            from_state TEXT NOT NULL,
            to_state TEXT NOT NULL,
            actor TEXT NOT NULL CHECK (char_length(actor) BETWEEN 1 AND 200),
            reason TEXT NOT NULL CHECK (char_length(reason) BETWEEN 1 AND 1000),
            created_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX case_transitions_case_id_idx ON case_transitions (case_id)")
    op.execute(
        """
        CREATE TABLE audit_chain_state (
            id SMALLINT PRIMARY KEY CHECK (id = 1),
            next_sequence BIGINT NOT NULL CHECK (next_sequence > 0),
            head_hash TEXT NOT NULL CHECK (head_hash ~ '^[0-9a-f]{64}$')
        )
        """
    )
    op.execute(
        f"""
        INSERT INTO audit_chain_state (id, next_sequence, head_hash)
        VALUES (1, 1, '{GENESIS_HASH}')
        """
    )
    op.execute(
        """
        CREATE TABLE audit_events (
            id UUID PRIMARY KEY,
            sequence BIGINT NOT NULL UNIQUE CHECK (sequence > 0),
            event_timestamp TIMESTAMPTZ NOT NULL,
            actor TEXT NOT NULL CHECK (char_length(actor) BETWEEN 1 AND 200),
            event_type TEXT NOT NULL CHECK (char_length(event_type) BETWEEN 1 AND 100),
            target_id UUID NULL REFERENCES targets (id),
            case_id UUID NULL REFERENCES cases (id),
            payload JSONB NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
            previous_event_hash TEXT NOT NULL CHECK (previous_event_hash ~ '^[0-9a-f]{64}$'),
            event_hash TEXT NOT NULL UNIQUE CHECK (event_hash ~ '^[0-9a-f]{64}$')
        )
        """
    )
    op.execute("CREATE INDEX audit_events_target_id_idx ON audit_events (target_id)")
    op.execute("CREATE INDEX audit_events_case_id_idx ON audit_events (case_id)")
    op.execute(
        """
        CREATE FUNCTION synapse_reject_audit_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events are append-only'
                USING ERRCODE = '55000';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW
        EXECUTE FUNCTION synapse_reject_audit_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_no_truncate
        BEFORE TRUNCATE ON audit_events
        FOR EACH STATEMENT
        EXECUTE FUNCTION synapse_reject_audit_mutation()
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'synapse_app') THEN
                GRANT USAGE ON SCHEMA public TO synapse_app;
                GRANT SELECT, INSERT, UPDATE ON targets TO synapse_app;
                GRANT SELECT, INSERT, UPDATE ON cases TO synapse_app;
                GRANT SELECT, INSERT ON case_transitions TO synapse_app;
                GRANT SELECT, UPDATE ON audit_chain_state TO synapse_app;
                GRANT SELECT, INSERT ON audit_events TO synapse_app;
            END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_truncate ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events")
    op.execute("DROP TABLE IF EXISTS audit_events")
    op.execute("DROP TABLE IF EXISTS case_transitions")
    op.execute("DROP TABLE IF EXISTS cases")
    op.execute("DROP TABLE IF EXISTS targets")
    op.execute("DROP TABLE IF EXISTS audit_chain_state")
    op.execute("DROP FUNCTION IF EXISTS synapse_reject_audit_mutation()")

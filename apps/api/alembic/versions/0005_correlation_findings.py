"""Derived correlation links and findings. Telemetry remains append-only.

Revision ID: 0005_correlation_findings
Revises: 0004_agent_enrollment
Create Date: 2026-11-04

synapse_app may SELECT/INSERT correlation_runs and correlation_links,
and SELECT/INSERT/UPDATE findings. It cannot DELETE derived rows or
mutate telemetry_events.
"""

from alembic import op

revision = "0005_correlation_findings"
down_revision = "0004_agent_enrollment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE correlation_runs (
            id UUID PRIMARY KEY,
            target_id UUID NOT NULL REFERENCES targets (id),
            window_seconds INTEGER NOT NULL CHECK (
                window_seconds >= 1 AND window_seconds <= 3600
            ),
            event_count INTEGER NOT NULL CHECK (event_count >= 0),
            link_count INTEGER NOT NULL CHECK (link_count >= 0),
            finding_count INTEGER NOT NULL CHECK (finding_count >= 0),
            risk_score INTEGER NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
            risk_factors JSONB NOT NULL CHECK (jsonb_typeof(risk_factors) = 'array'),
            formula TEXT NOT NULL,
            actor TEXT NOT NULL CHECK (char_length(actor) BETWEEN 1 AND 200),
            created_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX correlation_runs_target_id_idx ON correlation_runs (target_id, created_at)"
    )
    op.execute(
        """
        CREATE TABLE correlation_links (
            id UUID PRIMARY KEY,
            run_id UUID NOT NULL REFERENCES correlation_runs (id),
            target_id UUID NOT NULL REFERENCES targets (id),
            rule_id TEXT NOT NULL CHECK (char_length(rule_id) BETWEEN 1 AND 80),
            left_event_id UUID NOT NULL REFERENCES telemetry_events (event_id),
            right_event_id UUID NOT NULL REFERENCES telemetry_events (event_id),
            agent_id UUID NOT NULL,
            boot_id UUID NOT NULL,
            process_pid INTEGER,
            process_start_ticks BIGINT,
            window_seconds INTEGER NOT NULL CHECK (
                window_seconds >= 1 AND window_seconds <= 3600
            ),
            reason TEXT NOT NULL CHECK (char_length(reason) BETWEEN 1 AND 1000),
            left_observed_at TIMESTAMPTZ NOT NULL,
            right_observed_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT correlation_links_pair_key UNIQUE (
                target_id, rule_id, left_event_id, right_event_id
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX correlation_links_target_id_idx ON correlation_links (target_id, rule_id)"
    )
    op.execute(
        """
        CREATE TABLE findings (
            id UUID PRIMARY KEY,
            fingerprint TEXT NOT NULL UNIQUE CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
            target_id UUID NOT NULL REFERENCES targets (id),
            agent_id UUID NOT NULL,
            boot_id UUID NOT NULL,
            finding_type TEXT NOT NULL CHECK (
                finding_type IN (
                    'lifecycle_exit_without_start',
                    'lifecycle_pid_reuse_unresolved',
                    'repeated_network_activity',
                    'multi_port_network_activity',
                    'rapid_activity_burst',
                    'repeated_observation_pattern'
                )
            ),
            severity TEXT NOT NULL CHECK (severity IN ('info', 'low', 'medium', 'high')),
            evidence_strength TEXT NOT NULL CHECK (
                evidence_strength IN ('low', 'medium', 'high')
            ),
            confidence DOUBLE PRECISION NOT NULL CHECK (
                confidence >= 0 AND confidence <= 1
            ),
            epistemic_status TEXT NOT NULL CHECK (
                epistemic_status IN ('correlation', 'inference')
            ),
            supporting_event_ids JSONB NOT NULL CHECK (
                jsonb_typeof(supporting_event_ids) = 'array'
            ),
            explanation TEXT NOT NULL CHECK (char_length(explanation) BETWEEN 1 AND 2000),
            rules_triggered JSONB NOT NULL CHECK (jsonb_typeof(rules_triggered) = 'array'),
            missing_evidence JSONB NOT NULL CHECK (jsonb_typeof(missing_evidence) = 'array'),
            risk_contribution INTEGER NOT NULL CHECK (
                risk_contribution >= 0 AND risk_contribution <= 100
            ),
            risk_factors JSONB NOT NULL CHECK (jsonb_typeof(risk_factors) = 'array'),
            subject_key TEXT NOT NULL CHECK (char_length(subject_key) BETWEEN 1 AND 500),
            window_seconds INTEGER NOT NULL CHECK (
                window_seconds >= 1 AND window_seconds <= 3600
            ),
            last_run_id UUID NOT NULL REFERENCES correlation_runs (id),
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX findings_target_id_idx ON findings (target_id, created_at)")
    op.execute("CREATE INDEX findings_type_idx ON findings (finding_type)")
    op.execute(
        """
        CREATE FUNCTION synapse_enforce_finding_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id THEN
                RAISE EXCEPTION 'finding id is immutable' USING ERRCODE = '55000';
            END IF;
            IF NEW.fingerprint IS DISTINCT FROM OLD.fingerprint THEN
                RAISE EXCEPTION 'finding fingerprint is immutable' USING ERRCODE = '55000';
            END IF;
            IF NEW.target_id IS DISTINCT FROM OLD.target_id THEN
                RAISE EXCEPTION 'finding target is immutable' USING ERRCODE = '55000';
            END IF;
            IF NEW.finding_type IS DISTINCT FROM OLD.finding_type THEN
                RAISE EXCEPTION 'finding type is immutable' USING ERRCODE = '55000';
            END IF;
            IF NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'finding created_at is immutable' USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER findings_enforce_update
        BEFORE UPDATE ON findings
        FOR EACH ROW
        EXECUTE FUNCTION synapse_enforce_finding_update()
        """
    )
    op.execute(
        """
        CREATE FUNCTION synapse_reject_correlation_delete()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'correlation rows cannot be deleted by this role'
                USING ERRCODE = '55000';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER correlation_runs_no_delete
        BEFORE DELETE ON correlation_runs
        FOR EACH ROW
        EXECUTE FUNCTION synapse_reject_correlation_delete()
        """
    )
    op.execute(
        """
        CREATE TRIGGER correlation_links_no_delete
        BEFORE DELETE ON correlation_links
        FOR EACH ROW
        EXECUTE FUNCTION synapse_reject_correlation_delete()
        """
    )
    op.execute(
        """
        CREATE TRIGGER findings_no_delete
        BEFORE DELETE ON findings
        FOR EACH ROW
        EXECUTE FUNCTION synapse_reject_correlation_delete()
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
            GRANT SELECT, INSERT ON correlation_runs TO synapse_app;
            GRANT SELECT, INSERT ON correlation_links TO synapse_app;
            GRANT SELECT, INSERT, UPDATE ON findings TO synapse_app;
        END
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS findings_no_delete ON findings")
    op.execute("DROP TRIGGER IF EXISTS correlation_links_no_delete ON correlation_links")
    op.execute("DROP TRIGGER IF EXISTS correlation_runs_no_delete ON correlation_runs")
    op.execute("DROP TRIGGER IF EXISTS findings_enforce_update ON findings")
    op.execute("DROP TABLE IF EXISTS findings")
    op.execute("DROP TABLE IF EXISTS correlation_links")
    op.execute("DROP TABLE IF EXISTS correlation_runs")
    op.execute("DROP FUNCTION IF EXISTS synapse_enforce_finding_update()")
    op.execute("DROP FUNCTION IF EXISTS synapse_reject_correlation_delete()")

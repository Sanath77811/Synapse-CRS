"""Derived reconstructions, assessments, and verified recommendations.

Revision ID: 0006_hybrid_reasoning
Revises: 0005_correlation_findings
Create Date: 2026-11-04

Original telemetry is unchanged. synapse_app may SELECT/INSERT these
tables and UPDATE assessments on fingerprint match. No DELETE grant.
"""

from alembic import op

revision = "0006_hybrid_reasoning"
down_revision = "0005_correlation_findings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE reasoning_reconstructions (
            id UUID PRIMARY KEY,
            target_id UUID NOT NULL REFERENCES targets (id),
            dataset_label TEXT NOT NULL CHECK (
                dataset_label IN ('synthetic_lab', 'live_collector', 'unspecified')
            ),
            event_ids JSONB NOT NULL CHECK (jsonb_typeof(event_ids) = 'array'),
            quality JSONB NOT NULL CHECK (jsonb_typeof(quality) = 'object'),
            timeline JSONB NOT NULL CHECK (jsonb_typeof(timeline) = 'array'),
            process_count INTEGER NOT NULL CHECK (process_count >= 0),
            graph_nodes INTEGER NOT NULL CHECK (graph_nodes >= 0),
            graph_edges INTEGER NOT NULL CHECK (graph_edges >= 0),
            missing_evidence JSONB NOT NULL CHECK (jsonb_typeof(missing_evidence) = 'array'),
            created_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX reasoning_reconstructions_target_idx "
        "ON reasoning_reconstructions (target_id, created_at)"
    )
    op.execute(
        """
        CREATE TABLE reasoning_assessments (
            id UUID PRIMARY KEY,
            fingerprint TEXT NOT NULL UNIQUE CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
            target_id UUID NOT NULL REFERENCES targets (id),
            reconstruction_id UUID NOT NULL REFERENCES reasoning_reconstructions (id),
            engine_version TEXT NOT NULL,
            dataset_label TEXT NOT NULL,
            selected_hypothesis TEXT NOT NULL,
            confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
            severity TEXT NOT NULL CHECK (severity IN ('info', 'low', 'medium', 'high')),
            body JSONB NOT NULL CHECK (jsonb_typeof(body) = 'object'),
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX reasoning_assessments_target_idx "
        "ON reasoning_assessments (target_id, created_at)"
    )
    op.execute(
        """
        CREATE TABLE reasoning_proposals (
            id UUID PRIMARY KEY,
            assessment_id UUID NOT NULL REFERENCES reasoning_assessments (id),
            target_id UUID NOT NULL REFERENCES targets (id),
            kind TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            solver_result TEXT NOT NULL,
            body JSONB NOT NULL CHECK (jsonb_typeof(body) = 'object'),
            created_at TIMESTAMPTZ NOT NULL
        )
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
            GRANT SELECT, INSERT ON reasoning_reconstructions TO synapse_app;
            GRANT SELECT, INSERT, UPDATE ON reasoning_assessments TO synapse_app;
            GRANT SELECT, INSERT ON reasoning_proposals TO synapse_app;
        END
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reasoning_proposals")
    op.execute("DROP TABLE IF EXISTS reasoning_assessments")
    op.execute("DROP TABLE IF EXISTS reasoning_reconstructions")

"""Constrain revocation and case transitions for the application role.

Revision ID: 0002_enforce_state
Revises: 0001_initial
Create Date: 2026-09-26
"""

from alembic import op

revision = "0002_enforce_state"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'synapse_app') THEN
                RAISE EXCEPTION 'synapse_app role must exist before privileges are granted'
                    USING ERRCODE = '42501';
            END IF;
            REVOKE UPDATE ON targets FROM synapse_app;
            REVOKE UPDATE ON cases FROM synapse_app;
            GRANT UPDATE (authorization_status, updated_at) ON targets TO synapse_app;
            GRANT UPDATE (state, updated_at) ON cases TO synapse_app;
        END
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION synapse_enforce_target_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.authorization_status IS DISTINCT FROM OLD.authorization_status
               AND (
                    OLD.authorization_status IS DISTINCT FROM 'active'
                    OR NEW.authorization_status IS DISTINCT FROM 'revoked'
               )
            THEN
                RAISE EXCEPTION 'authorization revocation is one-way'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER targets_revocation_one_way
        BEFORE UPDATE ON targets
        FOR EACH ROW
        EXECUTE FUNCTION synapse_enforce_target_update()
        """
    )
    op.execute(
        """
        CREATE FUNCTION synapse_enforce_case_insert()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.state IS DISTINCT FROM 'AUTHORIZED_TARGET' THEN
                RAISE EXCEPTION 'case transition is not allowed'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER cases_insert_initial_state
        BEFORE INSERT ON cases
        FOR EACH ROW
        EXECUTE FUNCTION synapse_enforce_case_insert()
        """
    )
    op.execute(
        """
        CREATE FUNCTION synapse_enforce_case_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.state IS NOT DISTINCT FROM OLD.state THEN
                RETURN NEW;
            END IF;
            IF NOT (
                (OLD.state = 'AUTHORIZED_TARGET' AND NEW.state = 'OBSERVATION')
                OR (OLD.state = 'OBSERVATION' AND NEW.state = 'EVIDENCE')
                OR (OLD.state = 'EVIDENCE' AND NEW.state = 'HYPOTHESIS')
                OR (OLD.state = 'HYPOTHESIS' AND NEW.state = 'VERIFICATION')
                OR (OLD.state = 'VERIFICATION' AND NEW.state = 'APPROVAL')
                OR (OLD.state = 'APPROVAL' AND NEW.state = 'ACTION')
                OR (OLD.state = 'ACTION' AND NEW.state = 'VALIDATION')
                OR (OLD.state = 'VALIDATION' AND NEW.state = 'ROLLBACK')
                OR (OLD.state = 'ROLLBACK' AND NEW.state = 'SEALED_AUDIT')
            ) THEN
                RAISE EXCEPTION 'case transition is not allowed'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER cases_forward_only
        BEFORE UPDATE ON cases
        FOR EACH ROW
        EXECUTE FUNCTION synapse_enforce_case_update()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS cases_forward_only ON cases")
    op.execute("DROP TRIGGER IF EXISTS cases_insert_initial_state ON cases")
    op.execute("DROP TRIGGER IF EXISTS targets_revocation_one_way ON targets")
    op.execute("DROP FUNCTION IF EXISTS synapse_enforce_case_update()")
    op.execute("DROP FUNCTION IF EXISTS synapse_enforce_case_insert()")
    op.execute("DROP FUNCTION IF EXISTS synapse_enforce_target_update()")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'synapse_app') THEN
                GRANT UPDATE ON targets TO synapse_app;
                GRANT UPDATE ON cases TO synapse_app;
            END IF;
        END
        $$
        """
    )

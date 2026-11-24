"""
0002 — Fix documents RLS superadmin bypass policy.

Replaces the broken auth.uid() call (Supabase-only) with a session variable
check consistent with the rest of the RLS policies in this codebase.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-24
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the broken policy (uses auth.uid() which doesn't exist in vanilla PostgreSQL)
    op.execute("DROP POLICY IF EXISTS documents_isolation ON documents")

    # Replace with session-variable-based superadmin bypass (consistent with all other policies)
    op.execute("""
        CREATE POLICY documents_isolation ON documents
        USING (
            organization_id::text = current_setting('app.current_organization_id', TRUE)
            OR current_setting('app.is_superadmin', TRUE) = 'true'
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS documents_isolation ON documents")

    # Restore previous (broken) policy for downgrade completeness
    op.execute("""
        CREATE POLICY documents_isolation ON documents
        USING (
            organization_id::text = current_setting('app.current_organization_id', TRUE)
        )
    """)

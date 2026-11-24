"""
0001 — Initial schema with all tables and RLS policies.

Revision ID: 0001
Revises:
Create Date: 2026-11-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("is_verified", sa.Boolean, nullable=False, default=False),
        sa.Column("is_superadmin", sa.Boolean, nullable=False, default=False),
        sa.Column("verification_token", sa.String(128), nullable=True),
        sa.Column("reset_token", sa.String(128), nullable=True),
        sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_verification_token", "users", ["verification_token"])
    op.create_index("ix_users_reset_token", "users", ["reset_token"])

    # ── Organizations ─────────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("logo_url", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("plan", sa.String(50), nullable=False, default="free"),
        sa.Column("documents_used", sa.Integer, nullable=False, default=0),
        sa.Column("documents_limit", sa.Integer, nullable=False, default=100),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    # ── Organization Memberships ───────────────────────────────────────────────
    op.create_table(
        "organization_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, default="member"),
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_membership"),
    )
    op.create_index("ix_org_memberships_org_id", "organization_memberships", ["organization_id"])
    op.create_index("ix_org_memberships_user_id", "organization_memberships", ["user_id"])

    # ── Documents ─────────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("storage_key", sa.Text, nullable=False, unique=True),
        sa.Column("storage_bucket", sa.String(100), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, default="uploaded"),
        sa.Column("status_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_org_id", "documents", ["organization_id"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # ── Extractions ───────────────────────────────────────────────────────────
    op.create_table(
        "extractions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("extracted_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence_scores", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("overall_confidence", sa.Float, nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=True),
        sa.Column("processing_time_ms", sa.Integer, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, default="pending_review"),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("corrected_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extractions_document_id", "extractions", ["document_id"])
    op.create_index("ix_extractions_org_id", "extractions", ["organization_id"])
    op.create_index("ix_extractions_status", "extractions", ["status"])

    # ── Processing Jobs ───────────────────────────────────────────────────────
    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("task_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, default="pending"),
        sa.Column("attempt", sa.Integer, nullable=False, default=1),
        sa.Column("max_attempts", sa.Integer, nullable=False, default=3),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_detail", postgresql.JSONB, nullable=True),
        sa.Column("result_summary", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Audit Logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("success", sa.Boolean, nullable=False, default=True),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_org_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])

    # ── API Keys ──────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("hashed_key", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Webhooks ──────────────────────────────────────────────────────────────
    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("hashed_secret", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("events", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, default=30),
        sa.Column("max_retries", sa.Integer, nullable=False, default=3),
        sa.Column("successful_deliveries", sa.Integer, nullable=False, default=0),
        sa.Column("failed_deliveries", sa.Integer, nullable=False, default=0),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("webhook_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_id", sa.String(100), nullable=False, unique=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(30), nullable=False, default="pending"),
        sa.Column("attempt", sa.Integer, nullable=False, default=1),
        sa.Column("response_status_code", sa.Integer, nullable=True),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Row-Level Security Policies ───────────────────────────────────────────
    # Enable RLS on all tenant-scoped tables
    for table in [
        "documents", "extractions", "processing_jobs", "audit_logs",
        "api_keys", "webhooks", "webhook_deliveries", "organization_memberships",
    ]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # Documents: org members see their org; superadmin bypasses via app.is_superadmin session var
    op.execute("""
        CREATE POLICY documents_isolation ON documents
        USING (
            organization_id::text = current_setting('app.current_organization_id', TRUE)
            OR current_setting('app.is_superadmin', TRUE) = 'true'
        )
    """)

    op.execute("""
        CREATE POLICY extractions_isolation ON extractions
        USING (
            organization_id::text = current_setting('app.current_organization_id', TRUE)
        )
    """)

    op.execute("""
        CREATE POLICY jobs_isolation ON processing_jobs
        USING (
            organization_id::text = current_setting('app.current_organization_id', TRUE)
        )
    """)

    op.execute("""
        CREATE POLICY audit_logs_isolation ON audit_logs
        USING (
            organization_id::text = current_setting('app.current_organization_id', TRUE)
            OR organization_id IS NULL
        )
    """)

    op.execute("""
        CREATE POLICY api_keys_isolation ON api_keys
        USING (
            organization_id::text = current_setting('app.current_organization_id', TRUE)
        )
    """)

    op.execute("""
        CREATE POLICY webhooks_isolation ON webhooks
        USING (
            organization_id::text = current_setting('app.current_organization_id', TRUE)
        )
    """)

    op.execute("""
        CREATE POLICY webhook_deliveries_isolation ON webhook_deliveries
        USING (
            organization_id::text = current_setting('app.current_organization_id', TRUE)
        )
    """)

    op.execute("""
        CREATE POLICY memberships_isolation ON organization_memberships
        USING (
            organization_id::text = current_setting('app.current_organization_id', TRUE)
        )
    """)


def downgrade() -> None:
    for table in ["webhook_deliveries", "webhooks", "api_keys", "audit_logs",
                   "processing_jobs", "extractions", "documents",
                   "organization_memberships", "organizations", "users"]:
        op.drop_table(table)

"""
0003 — Add missing indexes for query performance.

The initial schema indexed documents.organization_id and documents.status,
but left extractions, processing_jobs, and audit_logs without indexes on
their most-queried columns. These are needed for fast pagination and joins.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-24
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # extractions — frequently joined to documents, filtered by org
    op.create_index("ix_extractions_document_id", "extractions", ["document_id"])
    op.create_index("ix_extractions_organization_id", "extractions", ["organization_id"])
    # Composite for status-filtered list queries
    op.create_index(
        "ix_extractions_org_status",
        "extractions",
        ["organization_id", "status"],
    )

    # processing_jobs — worker lookups by document_id and celery_task_id
    op.create_index("ix_processing_jobs_document_id", "processing_jobs", ["document_id"])
    op.create_index("ix_processing_jobs_organization_id", "processing_jobs", ["organization_id"])

    # audit_logs — paginated reads per org, and per-user activity feeds
    op.create_index(
        "ix_audit_logs_organization_id_created_at",
        "audit_logs",
        ["organization_id", "created_at"],
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])

    # api_keys — lookup by org to list keys in settings UI
    op.create_index("ix_api_keys_organization_id", "api_keys", ["organization_id"])

    # webhooks — lookup by org
    op.create_index("ix_webhooks_organization_id", "webhooks", ["organization_id"])

    # webhook_deliveries — foreign key lookups
    op.create_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"])
    op.create_index(
        "ix_webhook_deliveries_organization_id",
        "webhook_deliveries",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_organization_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_webhook_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhooks_organization_id", table_name="webhooks")
    op.drop_index("ix_api_keys_organization_id", table_name="api_keys")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_organization_id_created_at", table_name="audit_logs")
    op.drop_index("ix_processing_jobs_organization_id", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_document_id", table_name="processing_jobs")
    op.drop_index("ix_extractions_org_status", table_name="extractions")
    op.drop_index("ix_extractions_organization_id", table_name="extractions")
    op.drop_index("ix_extractions_document_id", table_name="extractions")

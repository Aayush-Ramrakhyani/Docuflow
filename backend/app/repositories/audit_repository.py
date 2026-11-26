"""
Audit log repository — INSERT-only (never update or delete).

The audit trail is append-only by design: tampering with history should be
impossible through the application. Only two operations exist: write an entry
and read a tenant's entries.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        action: str,
        actor_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        success: bool = True,
        failure_reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        # Record who did what, to which resource, from where, and whether it succeeded.
        # The `metadata` arg maps to the model's `event_metadata` attribute (see audit.py).
        entry = AuditLog(
            action=action,
            actor_id=actor_id,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            event_metadata=metadata or {},
            success=success,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        await self.db.flush()  # Flush (not commit) — the caller's transaction owns the commit
        return entry

    async def list_for_org(
        self,
        organization_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        action_filter: str | None = None,
    ) -> list[AuditLog]:
        # Always scoped to one org — the audit log is tenant-private
        query = select(AuditLog).where(AuditLog.organization_id == organization_id)
        if action_filter:
            # Prefix match, e.g. "document." returns all document.* actions
            query = query.where(AuditLog.action.like(f"{action_filter}%"))
        # Newest first, paginated
        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

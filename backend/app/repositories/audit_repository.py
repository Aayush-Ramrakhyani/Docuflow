"""Audit log repository. INSERT-only — no updates or deletes."""

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
        entry = AuditLog(
            action=action,
            actor_id=actor_id,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            metadata=metadata or {},
            success=success,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_for_org(
        self,
        organization_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        action_filter: str | None = None,
    ) -> list[AuditLog]:
        query = select(AuditLog).where(AuditLog.organization_id == organization_id)
        if action_filter:
            query = query.where(AuditLog.action.like(f"{action_filter}%"))
        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

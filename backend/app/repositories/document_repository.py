"""
Document data access layer.

Every read and delete takes an organization_id and filters on it. This is the
application-level tenant guard that sits in front of PostgreSQL RLS — defense in
depth: even if RLS were misconfigured, a query here still can't cross tenants.
"""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, document_id: uuid.UUID, organization_id: uuid.UUID) -> Document | None:
        # Both id AND org must match — prevents IDOR across tenants
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        organization_id: uuid.UUID,
        status: str | None = None,
        document_type: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Document], int]:
        # Base query + a parallel count query, both org-scoped
        query = select(Document).where(Document.organization_id == organization_id)
        count_query = select(func.count()).select_from(Document).where(
            Document.organization_id == organization_id
        )

        # Optional filters applied identically to both queries so totals stay correct
        if status:
            query = query.where(Document.status == status)
            count_query = count_query.where(Document.status == status)
        if document_type:
            query = query.where(Document.document_type == document_type)
            count_query = count_query.where(Document.document_type == document_type)
        if search:
            # Parameterized ILIKE — bound param, never string concatenation (no SQLi)
            pattern = f"%{search}%"
            query = query.where(Document.original_filename.ilike(pattern))
            count_query = count_query.where(Document.original_filename.ilike(pattern))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Newest first, then paginate
        query = query.order_by(Document.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create(
        self,
        organization_id: uuid.UUID,
        uploaded_by_id: uuid.UUID,
        original_filename: str,
        file_size_bytes: int,
        mime_type: str,
        storage_key: str,
        storage_bucket: str,
    ) -> Document:
        doc = Document(
            organization_id=organization_id,
            uploaded_by_id=uploaded_by_id,
            original_filename=original_filename,  # Display metadata only — never used as a path
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            storage_key=storage_key,
            storage_bucket=storage_bucket,
        )
        self.db.add(doc)
        await self.db.flush()  # Populate doc.id for the caller
        return doc

    async def update_status(
        self,
        document_id: uuid.UUID,
        status: str,
        status_message: str | None = None,
    ) -> None:
        # Sparse update — only overwrite status_message when one is supplied
        values: dict = {"status": status}
        if status_message is not None:
            values["status_message"] = status_message
        await self.db.execute(
            update(Document).where(Document.id == document_id).values(**values)
        )

    async def update_metadata(
        self,
        document_id: uuid.UUID,
        page_count: int | None = None,
        document_type: str | None = None,
    ) -> None:
        values: dict = {}
        if page_count is not None:
            values["page_count"] = page_count
        if document_type is not None:
            values["document_type"] = document_type
        if values:  # Skip the round-trip entirely if nothing changed
            await self.db.execute(
                update(Document).where(Document.id == document_id).values(**values)
            )

    async def delete(self, document_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
        # Org-scoped fetch first so one tenant can't delete another's document
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.organization_id == organization_id,
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return False  # Not found (or not this tenant's) — caller turns this into 404
        await self.db.delete(doc)
        return True

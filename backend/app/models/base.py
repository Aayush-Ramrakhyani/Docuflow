"""
Shared base class for all ORM models.

TimestampedModel provides the three columns every table needs: a UUID primary
key plus created_at / updated_at audit timestamps. Models inherit from it so
these are defined in exactly one place.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimestampedModel(Base):
    __abstract__ = True  # No table of its own — only subclasses get tables

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,  # UUIDv4 PKs — non-sequential, so IDs can't be enumerated
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),  # Set by the DB on INSERT
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),  # Automatically bumped by the DB on every UPDATE
        nullable=False,
    )

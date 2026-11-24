"""
Async SQLAlchemy engine, session factory, and base model setup.
RLS context is set per-session via app.current_organization_id.
Superadmin sessions set app.is_superadmin = 'true' to bypass org-scoped policies.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, MappedColumn
from sqlalchemy import text

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a plain DB session (no RLS context)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_rls_db(organization_id: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Yields a session with RLS context set.
    Use for all tenant-scoped queries.
    """
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                text("SELECT set_config('app.current_organization_id', :org_id, TRUE)"),
                {"org_id": str(organization_id)},
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def rls_session(organization_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Context manager for RLS-scoped sessions (for use in workers/services)."""
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                text("SELECT set_config('app.current_organization_id', :org_id, TRUE)"),
                {"org_id": str(organization_id)},
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def superadmin_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for superadmin sessions.
    Sets app.is_superadmin = 'true' to bypass org-scoped RLS policies.
    Only use after verifying the caller is a superadmin at the application layer.
    """
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                text("SELECT set_config('app.is_superadmin', 'true', TRUE)")
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

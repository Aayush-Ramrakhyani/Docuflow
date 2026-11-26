"""
Async SQLAlchemy engine, session factory, and declarative base.

Multi-tenancy note: tenant isolation is enforced at the database level via
PostgreSQL Row-Level Security (RLS). RLS policies read the per-session variable
`app.current_organization_id`, so any session touching tenant-scoped tables MUST
set it first. Use get_rls_db() / rls_session() for that — never plain get_db().
Superadmin sessions instead set `app.is_superadmin = 'true'` to bypass org scoping.
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

# Single engine per process; owns the underlying connection pool.
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,        # Base number of pooled connections
    max_overflow=settings.DATABASE_MAX_OVERFLOW,  # Extra connections allowed under load
    pool_pre_ping=True,                           # Recycle dead connections before handing them out
    echo=settings.DEBUG,                          # Log SQL only when debugging
)

# Session factory — expire_on_commit=False keeps ORM objects usable after commit.
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
            await session.commit()    # Commit once the handler returns cleanly
        except Exception:
            await session.rollback()  # Roll back on any error — no partial writes
            raise
        finally:
            await session.close()


async def get_rls_db(organization_id: str) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields a session scoped to one organization via RLS.
    Use for all tenant-scoped queries.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Scope the session to one org; TRUE = reset when the transaction ends
            await session.execute(
                text("SELECT set_config('app.current_organization_id', :org_id, TRUE)"),
                {"org_id": str(organization_id)},  # Parameterized — never string-concatenated
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
    """Context-manager variant of get_rls_db() — for Celery workers/services."""
    async with AsyncSessionLocal() as session:
        try:
            # Same tenant scoping, usable outside FastAPI's dependency system
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
    Only use AFTER verifying the caller is a superadmin at the application layer.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Flips the RLS escape hatch for cross-tenant admin operations only
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

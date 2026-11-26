"""
User data access layer.

Pure persistence — no business rules, no hashing, no HTTP concerns. Services call
these methods; the repository just translates them into SQL. Email is always
normalized (lowercased/trimmed) so lookups are case-insensitive.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        # Normalize before matching so "A@x.com" and "a@x.com " resolve to the same user
        result = await self.db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_by_verification_token(self, token: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.verification_token == token)
        )
        return result.scalar_one_or_none()

    async def get_by_reset_token(self, token: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.reset_token == token,
                User.reset_token_expires_at > datetime.now(UTC),  # Reject expired tokens at the query level
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        hashed_password: str,  # Caller must pass an already-hashed password
        full_name: str,
        verification_token: str | None = None,
    ) -> User:
        user = User(
            email=email.lower().strip(),  # Store normalized form
            hashed_password=hashed_password,
            full_name=full_name,
            verification_token=verification_token,
        )
        self.db.add(user)
        await self.db.flush()  # Flush to populate user.id without committing
        return user

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(UTC))
        )

    async def set_verified(self, user_id: uuid.UUID) -> None:
        # Mark verified AND clear the one-time token so it can't be reused
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_verified=True, verification_token=None)
        )

    async def set_password(self, user_id: uuid.UUID, hashed_password: str) -> None:
        # Changing the password also invalidates any outstanding reset token
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                hashed_password=hashed_password,
                reset_token=None,
                reset_token_expires_at=None,
            )
        )

    async def set_reset_token(
        self, user_id: uuid.UUID, token: str, expires_at: datetime
    ) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(reset_token=token, reset_token_expires_at=expires_at)
        )

    async def update_profile(
        self, user_id: uuid.UUID, full_name: str | None = None, avatar_url: str | None = None
    ) -> None:
        # Build a sparse update — only set fields that were actually provided
        values: dict = {}
        if full_name is not None:
            values["full_name"] = full_name
        if avatar_url is not None:
            values["avatar_url"] = avatar_url
        if values:
            await self.db.execute(update(User).where(User.id == user_id).values(**values))

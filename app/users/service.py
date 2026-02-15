from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import GoogleUserCreate


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.repository = UserRepository(db)

    async def get_or_create_google_user(self, google_data: GoogleUserCreate) -> User:
        """
        Find existing user by google_id or email.
        If not found, create a new user (sign-in without prior signup).
        """
        existing = await self.repository.get_by_google_id(google_data.google_id)
        if existing:
            return existing

        existing = await self.repository.get_by_email(google_data.email)
        if existing:
            return existing

        new_user = User(
            email=google_data.email,
            full_name=google_data.full_name,
            auth_provider="google",
            google_id=google_data.google_id,
            picture_url=google_data.picture_url,
        )
        return await self.repository.create(new_user)

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return await self.repository.get_by_id(user_id)

from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import GoogleUserCreate


class UserService:
    def __init__(self) -> None:
        self.repository = UserRepository()

    def get_or_create_google_user(self, google_data: GoogleUserCreate) -> User:
        """
        Find existing user by google_id or email.
        If not found, create a new user (sign-in without prior signup).
        """
        existing = self.repository.get_by_google_id(google_data.google_id)
        if existing:
            return existing

        existing = self.repository.get_by_email(google_data.email)
        if existing:
            return existing

        new_user = User(
            email=google_data.email,
            full_name=google_data.full_name,
            auth_provider="google",
            google_id=google_data.google_id,
            picture_url=google_data.picture_url,
        )
        return self.repository.create(new_user)

    def get_user_by_id(self, user_id: str) -> User | None:
        return self.repository.get_by_id(user_id)

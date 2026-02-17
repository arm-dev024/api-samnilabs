from datetime import datetime, timezone

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

    def update_subscription(
        self,
        user: User,
        plan_id: str,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        subscription_status: str = "active",
    ) -> User:
        user.subscription_plan_id = plan_id
        user.subscription_status = subscription_status
        user.subscribed_at = datetime.now(timezone.utc).isoformat()
        if stripe_customer_id:
            user.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id:
            user.stripe_subscription_id = stripe_subscription_id
        return self.repository.update(user)

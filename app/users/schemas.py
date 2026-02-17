from pydantic import BaseModel

from app.subscription.schemas import PricingPlan


class GoogleUserCreate(BaseModel):
    """Schema for creating a user from Google OAuth data."""

    email: str
    full_name: str
    google_id: str
    picture_url: str | None = None


class LocalUserCreate(BaseModel):
    """Schema for creating a user via local signup (future use)."""

    email: str
    full_name: str
    password: str  # Plain text -- will be hashed before storage


class UserResponse(BaseModel):
    """Public user representation returned by the API."""

    id: str
    email: str
    full_name: str
    auth_provider: str
    picture_url: str | None = None
    is_active: bool
    subscription_plan_id: str | None = None
    subscription_status: str = "none"
    subscribed_at: str | None = None
    subscription: PricingPlan | None = None

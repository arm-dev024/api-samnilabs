from uuid import UUID

from pydantic import BaseModel


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

    id: UUID
    email: str
    full_name: str
    auth_provider: str
    picture_url: str | None = None
    is_active: bool

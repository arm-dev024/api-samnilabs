from pydantic import BaseModel

from app.users.schemas import UserResponse


class TokenResponse(BaseModel):
    """Returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded JWT payload structure."""

    sub: str  # user ID
    email: str
    exp: int | None = None


class AuthResponse(BaseModel):
    """Returned after successful Google OAuth login."""

    user: UserResponse
    message: str = "Login successful"


class GoogleCallbackError(BaseModel):
    """Error response when Google OAuth callback fails."""

    error: str
    error_description: str | None = None

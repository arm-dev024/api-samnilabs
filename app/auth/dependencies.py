from fastapi import HTTPException, Request, status

from app.auth.service import AuthService
from app.users.models import User
from app.users.service import UserService


async def get_current_user(
    request: Request,
) -> User:
    """
    FastAPI dependency: extracts JWT from the access_token cookie,
    decodes it, and returns the corresponding User.
    """
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = AuthService.decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_service = UserService()
    user = user_service.get_user_by_id(payload.sub)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user

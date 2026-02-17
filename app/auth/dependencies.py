from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

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
    # If middleware already resolved the user, reuse it
    if hasattr(request.state, "user") and request.state.user is not None:
        return request.state.user

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


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that resolves the current user from the JWT cookie
    and attaches it to request.state.user for all routes.

    Non-authenticated requests get request.state.user = None (no error).
    Protected routes still use Depends(get_current_user) to enforce auth.
    """

    async def dispatch(self, request: Request, call_next):
        request.state.user = None

        token = request.cookies.get("access_token")
        if token:
            payload = AuthService.decode_access_token(token)
            if payload:
                user_service = UserService()
                user = user_service.get_user_by_id(payload.sub)
                if user and user.is_active:
                    request.state.user = user

        response = await call_next(request)
        return response

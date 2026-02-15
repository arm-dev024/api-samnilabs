import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.service import AuthService
from app.config import settings
from app.database import get_db
from app.users.models import User
from app.users.schemas import UserResponse
from app.users.service import UserService

router = APIRouter()

# In-memory state store for CSRF protection during OAuth flow.
# TODO [Production]: Replace with Redis or a short-lived DB-backed store with TTL.
_oauth_states: set[str] = set()


def _cookie_params() -> dict:
    """Cookie params based on environment.

    Production (api.samnilabs.ai <-> dashboard.samnilabs.ai):
      - domain=".samnilabs.ai" so the cookie is shared across subdomains
      - secure=True (HTTPS only)
      - samesite="none" (cross-subdomain requires this + Secure)

    Development (localhost):
      - No domain (defaults to the host that set it, i.e. localhost)
      - secure=False (localhost is HTTP)
      - samesite="lax" (standard browser default for same-site)
    """
    if settings.app_env == "development":
        return {
            "httponly": True,
            "secure": False,
            "samesite": "lax",
            "path": "/",
        }
    return {
        "httponly": True,
        "secure": True,
        "samesite": "none",
        "domain": ".samnilabs.ai",
        "path": "/",
    }


def _set_auth_cookie(response: Response, access_token: str) -> None:
    """Set the JWT access token as an HTTP-only cookie."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        **_cookie_params(),
    )


def _delete_auth_cookie(response: Response) -> None:
    """Delete the JWT access token cookie."""
    response.delete_cookie(
        key="access_token",
        **_cookie_params(),
    )


@router.get("/google/login")
async def google_login():
    """
    Redirect the user to Google's OAuth consent screen.
    The frontend calls this single route to initiate Google login.
    """
    state = secrets.token_urlsafe(32)
    _oauth_states.add(state)

    auth_url = AuthService.build_google_auth_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Google redirects here after the user consents or cancels.

    Success: Google sends ?code=...&state=...
    Cancellation: Google sends ?error=access_denied
    """

    # Handle user cancellation or Google errors
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_description or error,
        )

    # Validate required parameters
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code or state parameter",
        )

    # CSRF validation
    if state not in _oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter. Possible CSRF attack.",
        )
    _oauth_states.discard(state)

    # Exchange code for tokens
    try:
        token_data = await AuthService.exchange_code_for_tokens(code)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange authorization code with Google",
        )

    google_access_token = token_data.get("access_token")
    if not google_access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google did not return an access token",
        )

    # Fetch user info from Google
    try:
        google_user_data = await AuthService.get_google_user_info(google_access_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch user info from Google",
        )

    # Get or create user (auto sign-in without prior signup)
    user_service = UserService(db)
    user = await user_service.get_or_create_google_user(google_user_data)

    # Generate custom JWT
    access_token = AuthService.create_access_token(
        user_id=str(user.id),
        email=user.email,
    )

    # Set JWT cookie and redirect to frontend
    response = RedirectResponse(url=f"{settings.frontend_url}/auth/callback")
    _set_auth_cookie(response, access_token)
    return response


@router.get("/me", response_model=UserResponse)
async def get_current_user_route(
    current_user: User = Depends(get_current_user),
):
    """Returns the currently authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        auth_provider=current_user.auth_provider,
        picture_url=current_user.picture_url,
        is_active=current_user.is_active,
    )


@router.post("/logout")
async def logout():
    """Clear the access_token cookie to log the user out."""
    response = JSONResponse(content={"message": "Logged out"})
    _delete_auth_cookie(response)
    return response

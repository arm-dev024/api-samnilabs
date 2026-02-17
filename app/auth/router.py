import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth.dependencies import get_current_user
from app.auth.service import AuthService
from app.config import settings
from app.users.models import User
from app.users.schemas import UserResponse
from app.users.service import UserService

router = APIRouter()

# In-memory state store for CSRF protection during OAuth flow.
# Maps state token -> action (e.g. "login", "signup").
# TODO [Production]: Replace with Redis or a short-lived DB-backed store with TTL.
_oauth_states: dict[str, str] = {}


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
        max_age=settings.jwt.access_token_expire_minutes * 60,
        **_cookie_params(),
    )


def _delete_auth_cookie(response: Response) -> None:
    """Delete the JWT access token cookie."""
    response.delete_cookie(
        key="access_token",
        **_cookie_params(),
    )


def _error_redirect(message: str, action: str | None = None) -> RedirectResponse:
    """Redirect to the frontend auth callback with an error query parameter."""
    redirect_url = f"{str(settings.frontend_url).rstrip('/')}/auth/callback?error={quote(message)}&action={action}"
    print(f"DEBUG ERROR REDIRECT URL: {redirect_url}")
    return RedirectResponse(url=redirect_url)


@router.get("/google/login")
async def google_login(action: str = Query(default="login")):  # "login" | "signup"
    """
    Redirect the user to Google's OAuth consent screen.
    The frontend calls this route to initiate Google login or signup.

    Query params:
        action: "login" or "signup" (default: "login")
    """
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = action

    auth_url = AuthService.build_google_auth_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
):
    """
    Google redirects here after the user consents or cancels.

    Success: Google sends ?code=...&state=...
    Cancellation: Google sends ?error=access_denied
    """

    # Try to extract action from state (may be None if state is missing/invalid)
    action = _oauth_states.pop(state, None) if state else None

    # Handle user cancellation or Google errors
    if error:
        return _error_redirect(error_description or error, action)

    # Validate required parameters
    if not code or not state:
        return _error_redirect("missing_params", action)

    # CSRF validation
    if action is None:
        return _error_redirect("invalid_state")

    # Exchange code for tokens
    try:
        token_data = await AuthService.exchange_code_for_tokens(code)
    except Exception:
        return _error_redirect("token_exchange_failed", action)

    google_access_token = token_data.get("access_token")
    if not google_access_token:
        return _error_redirect("no_access_token", action)

    # Fetch user info from Google
    try:
        google_user_data = await AuthService.get_google_user_info(google_access_token)
    except Exception:
        return _error_redirect("user_info_failed", action)

    # Get or create user (auto sign-in without prior signup)
    user_service = UserService()
    user = user_service.get_or_create_google_user(google_user_data)

    # Generate custom JWT
    access_token = AuthService.create_access_token(
        user_id=str(user.id),
        email=user.email,
    )

    # Set JWT cookie and redirect to frontend
    redirect_url = f"{str(settings.frontend_url).rstrip('/')}/auth/callback?action={action}"
    print(f"DEBUG REDIRECT URL: {redirect_url}")
    response = RedirectResponse(url=redirect_url)
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
        subscription_plan_id=current_user.subscription_plan_id,
        subscription_status=current_user.subscription_status,
        subscribed_at=current_user.subscribed_at,
    )


@router.post("/logout")
async def logout():
    """Clear the access_token cookie to log the user out."""
    response = JSONResponse(content={"message": "Logged out"})
    _delete_auth_cookie(response)
    return response

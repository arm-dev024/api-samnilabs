from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.auth.schemas import TokenPayload
from app.config import settings
from app.users.schemas import GoogleUserCreate

# Password hashing context -- ready for future local auth
# TODO [Local Auth]: Use pwd_context.hash(password) and pwd_context.verify(plain, hashed)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:

    # --- JWT ---

    @staticmethod
    def create_access_token(user_id: str, email: str) -> str:
        """Create a custom JWT access token with user claims."""
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    @staticmethod
    def decode_access_token(token: str) -> TokenPayload | None:
        """Decode and validate a JWT token. Returns None if invalid/expired."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return TokenPayload(
                sub=payload.get("sub"),
                email=payload.get("email"),
                exp=payload.get("exp"),
            )
        except JWTError:
            return None

    # --- Google OAuth ---

    @staticmethod
    def build_google_auth_url(state: str) -> str:
        """Build the Google OAuth consent screen URL with CSRF state."""
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "state": state,
            "prompt": "consent",
        }
        return f"{settings.google_auth_url}?{urlencode(params)}"

    @staticmethod
    async def exchange_code_for_tokens(code: str) -> dict:
        """Exchange the authorization code for Google access/id tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.google_token_url,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_google_user_info(access_token: str) -> GoogleUserCreate:
        """Fetch the user's profile from Google's userinfo endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                settings.google_userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()

        return GoogleUserCreate(
            email=data["email"],
            full_name=data.get("name", ""),
            google_id=data["id"],
            picture_url=data.get("picture"),
        )

    # --- Password hashing (for future local auth) ---

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

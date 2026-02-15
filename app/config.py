from pathlib import Path
from typing import Literal
from pydantic import SecretStr, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App Metadata
    app_env: Literal["development", "testing", "production"] = "development"
    base_url: HttpUrl = "http://localhost:8000"
    frontend_url: HttpUrl = "http://localhost:5173"

    # Google OAuth
    google_client_id: str
    google_client_secret: SecretStr
    google_auth_url: HttpUrl = "https://accounts.google.com/o/oauth2/v2/auth"
    google_token_url: HttpUrl = "https://oauth2.googleapis.com/token"
    google_userinfo_url: HttpUrl = "https://www.googleapis.com/oauth2/v2/userinfo"

    # JWT
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # DynamoDB
    db_endpoint_url: HttpUrl = "http://localhost:8020"
    db_region: str = "us-east-1"
    db_table_name: str = "samnilabs_users"
    db_aws_access_key_id: str = "local"
    db_aws_secret_access_key: SecretStr = "local"

    @model_validator(mode="after")
    def production_must_use_production_urls(self) -> "Settings":
        if self.app_env != "production":
            return self
        frontend = str(self.frontend_url)
        if "localhost" in frontend or "127.0.0.1" in frontend:
            raise ValueError(
                "In production, FRONTEND_URL must not be localhost. "
                "Set FRONTEND_URL in your production environment (e.g. FRONTEND_URL=https://dashboard.samnilabs.ai)."
            )
        return self

    @property
    def google_redirect_uri(self) -> str:
        return f"{str(self.base_url).rstrip('/')}/auth/google/callback"


settings = Settings()

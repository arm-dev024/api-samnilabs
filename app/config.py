from typing import Literal
from pydantic import SecretStr, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class GoogleOAuthSettings(BaseSettings):
    client_id: str
    client_secret: SecretStr
    auth_url: HttpUrl = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url: HttpUrl = "https://oauth2.googleapis.com/token"
    userinfo_url: HttpUrl = "https://www.googleapis.com/oauth2/v2/userinfo"


class JWTSettings(BaseSettings):
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


class DynamoDBSettings(BaseSettings):
    endpoint_url: HttpUrl = "http://localhost:8020"
    region: str = "us-east-1"
    table_name: str = "samnilabs_users"
    aws_access_key_id: str = "local"
    aws_secret_access_key: SecretStr = "local"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # This allows you to use prefixes in your .env like GOOGLE_CLIENT_ID
        env_nested_delimiter="__",
    )

    # App Metadata
    app_env: Literal["development", "testing", "production"] = "development"
    base_url: HttpUrl = "http://localhost:8000"
    frontend_url: HttpUrl = "http://localhost:5173"

    # Nested Groups
    google: GoogleOAuthSettings
    jwt: JWTSettings
    db: DynamoDBSettings

    @property
    def google_redirect_uri(self) -> str:
        return f"{str(self.base_url).rstrip('/')}/auth/google/callback"


settings = Settings()

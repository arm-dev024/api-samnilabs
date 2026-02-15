from pathlib import Path
from typing import Literal
from pydantic import BaseModel, SecretStr, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GoogleOAuthSettings(BaseModel):
    client_id: str
    client_secret: SecretStr
    auth_url: HttpUrl = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url: HttpUrl = "https://oauth2.googleapis.com/token"
    userinfo_url: HttpUrl = "https://www.googleapis.com/oauth2/v2/userinfo"


class JWTSettings(BaseModel):
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


class DynamoDBSettings(BaseModel):
    endpoint_url: HttpUrl = "http://localhost:8020"
    region: str = "us-east-1"
    table_name: str = "samnilabs_users"
    aws_access_key_id: str = "local"
    aws_secret_access_key: SecretStr = "local"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        # This allows you to use prefixes in your .env like GOOGLE_CLIENT_ID
        env_nested_delimiter="__",
    )

    # App Metadata
    app_env: Literal["development", "testing", "production"] = "development"
    base_url: HttpUrl = "http://localhost:8000"
    frontend_url: HttpUrl = "http://localhost:5173"

    # Deepgram (STT/TTS)
    deepgram_api_key: SecretStr = ""
    deepgram_voice_id: str = "aura-2-thalia-en"

    # OpenAI (STT/LLM/TTS/Realtime)
    openai_api_key: SecretStr = ""
    openai_model: str = "gpt-4o-mini"

    # Nested Groups
    google: GoogleOAuthSettings
    jwt: JWTSettings
    db: DynamoDBSettings

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

    def print_env_summary(self) -> None:
        """Print loaded env summary (secrets masked)."""
        mask = "***"
        print("--- Config / env summary ---")
        print("App:")
        print(f"  app_env={self.app_env}")
        print(f"  base_url={self.base_url}")
        print(f"  frontend_url={self.frontend_url}")
        print("Google:")
        print(f"  client_id={self.google.client_id}")
        print(f"  client_secret={mask}")
        print(f"  auth_url={self.google.auth_url}")
        print("JWT:")
        print(f"  algorithm={self.jwt.algorithm}")
        print(f"  access_token_expire_minutes={self.jwt.access_token_expire_minutes}")
        print(f"  secret_key={mask}")
        print("DB:")
        print(f"  endpoint_url={self.db.endpoint_url}")
        print(f"  region={self.db.region}")
        print(f"  table_name={self.db.table_name}")
        print(f"  aws_access_key_id={self.db.aws_access_key_id}")
        print(f"  aws_secret_access_key={mask}")
        print("---")


settings = Settings()

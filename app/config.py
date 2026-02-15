from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Server
    port: int = os.getenv("PORT", 8000)
    host: str = os.getenv("HOST", "0.0.0.0")
    base_url: str = os.getenv("SERVER_URL", "http://localhost:8000")

    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = f"{base_url}/auth/google/callback"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30  # 30 minutes

    # App
    frontend_url: str = os.getenv(
        "FRONTEND_URL", "http://localhost:5173"
    )  # default to localhost:5173
    app_env: str = os.getenv("APP_ENV", "development")

    # DynamoDB
    dynamodb_endpoint_url: str = "http://localhost:8020"
    dynamodb_region: str = "us-east-1"
    dynamodb_table_name: str = "samnilabs_users"
    aws_access_key_id: str = "local"
    aws_secret_access_key: str = "local"

    # Google OAuth endpoints
    google_auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    google_token_url: str = "https://oauth2.googleapis.com/token"
    google_userinfo_url: str = "https://www.googleapis.com/oauth2/v2/userinfo"


settings = Settings()

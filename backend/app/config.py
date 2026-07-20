from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "智汇·研管"
    app_version: str = "0.1.0"

    # Database
    database_url: str = "***REMOVED***"

    # JWT
    jwt_secret_key: str = "***REMOVED***"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60 * 24  # 24 hours
    jwt_refresh_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Password
    password_min_length: int = 6

    # Zeabur deploy (overridden via env)
    cors_origins: list[str] = ["*"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

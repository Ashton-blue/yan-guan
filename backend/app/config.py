import os
import secrets
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "智汇·研管"
    app_version: str = "0.1.0"

    # Database - 使用环境变量，默认 SQLite 用于开发
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")

    # JWT - 使用环境变量或生成随机密钥
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60 * 24  # 24 hours
    jwt_refresh_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Password
    password_min_length: int = 6

    # CORS - 从环境变量读取，默认仅允许本地开发
    cors_origins: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

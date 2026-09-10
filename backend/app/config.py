import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/yan_guan")

    # JWT 配置（密钥零硬编码：必须通过环境变量注入，未设置时为空并在 validate() 中拦截）
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_DAYS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "1"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # 应用配置
    APP_NAME: str = os.getenv("APP_NAME", "研管系统")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.4.0")

    # CORS 配置
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")

    # DeepSeek 配置（密钥零硬编码：仅从环境变量读取，无 fallback）
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # 审计日志保留天数
    AUDIT_LOG_RETENTION_DAYS: int = 180

    @classmethod
    def validate(cls):
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY 未设置：请通过环境变量注入（密钥零硬编码约束）")

settings = Settings()
settings.validate()

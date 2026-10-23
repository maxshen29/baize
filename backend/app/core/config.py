"""平台配置：环境变量优先，.env 兜底。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 始终从 backend/ 目录加载 .env，避免在不同 cwd 下（如从项目根目录运行脚本）找不到配置
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "Baize Platform"
    API_V1_PREFIX: str = "/api/v1"

    # 数据库（PostgreSQL）
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "baize"
    POSTGRES_PASSWORD: str = "baize"
    POSTGRES_DB: str = "baize"
    DATABASE_URL: str | None = None  # 若设置则优先

    # 安全
    SECRET_KEY: str = "change-me-in-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCK_MINUTES: int = 15

    # CORS（逗号分隔白名单）
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()

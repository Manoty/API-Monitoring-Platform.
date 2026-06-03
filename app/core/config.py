from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "API Monitor"
    DEBUG: bool = False
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://monitor:monitor@localhost:5432/apimonitor"
    DATABASE_URL_SYNC: str = "postgresql://monitor:monitor@localhost:5432/apimonitor"

    # Redis + Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Monitoring defaults
    DEFAULT_CHECK_INTERVAL_SECONDS: int = 60
    DEFAULT_TIMEOUT_SECONDS: int = 10
    MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT: int = 3
    DEFAULT_LATENCY_THRESHOLD_MS: float = 2000.0

    # Data retention
    METRIC_RETENTION_DAYS: int = 90

    # Email alerts (optional, falls back to log)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    ALERT_FROM_EMAIL: str = "alerts@apimonitor.local"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
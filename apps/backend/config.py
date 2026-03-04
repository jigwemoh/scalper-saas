import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

logger = logging.getLogger("config")

_INSECURE_JWT = "insecure-dev-secret-change-in-production"
_INSECURE_BRIDGE = "dev-bridge-secret"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://scalper:scalper_dev_pass@localhost:5432/scalper_saas"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = _INSECURE_JWT
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # MT5 Bridge
    mt5_bridge_url: str = "http://localhost:9000"
    mt5_bridge_secret: str = _INSECURE_BRIDGE

    # Paystack
    paystack_secret_key: str = ""
    paystack_public_key: str = ""

    # App
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_secrets(self) -> None:
        """Raise on insecure defaults when running in production."""
        if self.app_env == "production":
            if self.jwt_secret_key == _INSECURE_JWT:
                raise RuntimeError("JWT_SECRET_KEY must be set to a secure value in production")
            if self.mt5_bridge_secret == _INSECURE_BRIDGE:
                raise RuntimeError("MT5_BRIDGE_SECRET must be set to a secure value in production")
        else:
            if self.jwt_secret_key == _INSECURE_JWT:
                logger.warning("Using insecure default JWT secret — set JWT_SECRET_KEY in .env for production")
            if self.mt5_bridge_secret == _INSECURE_BRIDGE:
                logger.warning("Using insecure default bridge secret — set MT5_BRIDGE_SECRET in .env for production")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validate_secrets()
    return s

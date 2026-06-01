from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    CREDENTIALS_ENC_KEY: str
    WETARSEEL_API_KEY: str
    WETARSEEL_WEBHOOK_SECRET: str

    ENVIRONMENT: str = "development"


settings = Settings()

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://cronas:cronas@localhost:5435/cronas"
    redis_url: str = "redis://localhost:6381/0"
    kafka_bootstrap_servers: str = "localhost:9094"
    jobs_run_topic: str = "cronas.run"
    jobs_retry_topic: str = "cronas.retry"
    jobs_dlq_topic: str = "cronas.dlq"
    watcher_poll_seconds: int = 5
    api_host: str = "127.0.0.1"
    api_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
from urllib.parse import quote_plus
import os


class Settings:
    def __init__(self) -> None:
        self.postgres_db = os.getenv("POSTGRES_DB", "saasguard")
        self.postgres_user = os.getenv("POSTGRES_USER", "saasguard")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "saasguard")
        self.postgres_host = os.getenv("POSTGRES_HOST", "postgres")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.minio_bucket = os.getenv("MINIO_BUCKET", "exports")
        self.minio_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

    @property
    def postgres_dsn(self) -> str:
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        return (
            f"postgresql://{user}:{password}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

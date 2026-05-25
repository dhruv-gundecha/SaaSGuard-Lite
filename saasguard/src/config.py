import os
from functools import lru_cache
from urllib.parse import quote_plus


class Settings:
    def __init__(self) -> None:
        self.environment = os.getenv("APP_ENV", "local")
        self.service_name = os.getenv("SERVICE_NAME", "saasguard-api")
        self.dev_seed_enabled = (
            os.getenv("DEV_SEED_ENABLED", "true").lower() == "true"
            if self.environment == "local"
            else os.getenv("DEV_SEED_ENABLED", "false").lower() == "true"
        )
        self.dev_auth_username_fallback_enabled = (
            os.getenv("DEV_AUTH_USERNAME_FALLBACK_ENABLED", "true").lower() == "true"
            if self.environment == "local"
            else os.getenv("DEV_AUTH_USERNAME_FALLBACK_ENABLED", "false").lower()
            == "true"
        )

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
        self.minio_presign_expiry_seconds = int(
            os.getenv("MINIO_PRESIGN_EXPIRY_SECONDS", "900")
        )

        self.app_host = os.getenv("APP_HOST", "0.0.0.0")
        self.app_port = int(os.getenv("APP_PORT", "8000"))
        self.cors_origins = tuple(
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS", "http://localhost:5173,http://localhost:3001"
            ).split(",")
            if origin.strip()
        )

        self.oidc_issuer = os.getenv(
            "OIDC_ISSUER", "http://auth.saasguard.local:8081/realms/saasguard"
        )
        self.oidc_jwks_url = os.getenv(
            "OIDC_JWKS_URL",
            "http://auth.saasguard.local:8081/realms/saasguard/protocol/openid-connect/certs",
        )
        self.oidc_audience = os.getenv("OIDC_AUDIENCE", "saasguard-api")
        self.oidc_algorithms = tuple(
            item.strip()
            for item in os.getenv("OIDC_ALGORITHMS", "RS256").split(",")
            if item.strip()
        )

        self.worker_metrics_port = int(os.getenv("WORKER_METRICS_PORT", "9101"))
        self.worker_retry_limit = int(os.getenv("WORKER_RETRY_LIMIT", "2"))
        self.worker_retry_delay_seconds = int(
            os.getenv("WORKER_RETRY_DELAY_SECONDS", "10")
        )
        self.metrics_tenant_labels_enabled = (
            os.getenv("METRICS_TENANT_LABELS_ENABLED", "true").lower() == "true"
        )
        self.export_request_rate_limit_count = int(
            os.getenv("EXPORT_REQUEST_RATE_LIMIT_COUNT", "5")
        )
        self.export_request_rate_limit_window_seconds = int(
            os.getenv("EXPORT_REQUEST_RATE_LIMIT_WINDOW_SECONDS", "60")
        )

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

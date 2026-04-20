import json
import logging
import sys
from datetime import datetime, timezone

from src.config import get_settings
from src.context import correlation_id_var, request_id_var, service_var


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        settings = get_settings()
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", None) or service_var.get(),
            "environment": settings.environment,
            "logger": record.name,
            "event_name": getattr(record, "event_name", record.name),
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None)
            or correlation_id_var.get(),
            "request_id": getattr(record, "request_id", None) or request_id_var.get(),
            "job_id": getattr(record, "job_id", None),
            "tenant_id": getattr(record, "tenant_id", None),
            "user_id": getattr(record, "user_id", None),
            "keycloak_sub": getattr(record, "keycloak_sub", None),
            "outcome": getattr(record, "outcome", None),
            "error_type": getattr(record, "error_type", None),
            "error_message": getattr(record, "error_message", None),
        }
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def log_event(
    logger: logging.Logger,
    level: int,
    event_name: str,
    message: str,
    **fields: object,
) -> None:
    logger.log(level, message, extra={"event_name": event_name, **fields})

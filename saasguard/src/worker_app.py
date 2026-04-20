from prometheus_client import start_http_server

from src.celery_app import celery_app
from src.config import get_settings
from src.logging_utils import configure_logging
from src.migrations import run_migrations


settings = get_settings()
configure_logging()
run_migrations()
start_http_server(settings.worker_metrics_port)

celery_app.autodiscover_tasks(["src"])

from celery import Celery

from src.config import get_settings


settings = get_settings()

celery_app = Celery("saasguard_lite", broker=settings.redis_url)
celery_app.conf.update(
    task_default_queue="exports",
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
)

import time
from collections import deque

from fastapi import HTTPException, status

from src.config import get_settings


_export_request_windows: dict[tuple[str, str], deque[float]] = {}


def check_export_request_rate_limit(*, user_id: str, tenant_id: str) -> None:
    settings = get_settings()
    key = (user_id, tenant_id)
    now = time.monotonic()
    window = _export_request_windows.setdefault(key, deque())
    cutoff = now - settings.export_request_rate_limit_window_seconds

    while window and window[0] < cutoff:
        window.popleft()

    if len(window) >= settings.export_request_rate_limit_count:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Export request rate limit exceeded",
        )

    window.append(now)


def reset_export_rate_limits() -> None:
    _export_request_windows.clear()

from contextvars import ContextVar


request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[str | None] = ContextVar(
    "correlation_id", default=None
)
service_var: ContextVar[str | None] = ContextVar("service", default=None)


def set_request_context(
    *, request_id: str | None = None, correlation_id: str | None = None, service: str
) -> dict[str, object]:
    tokens: dict[str, object] = {"service": service_var.set(service)}
    if request_id is not None:
        tokens["request_id"] = request_id_var.set(request_id)
    if correlation_id is not None:
        tokens["correlation_id"] = correlation_id_var.set(correlation_id)
    return tokens


def reset_request_context(tokens: dict[str, object]) -> None:
    if "request_id" in tokens:
        request_id_var.reset(tokens["request_id"])
    if "correlation_id" in tokens:
        correlation_id_var.reset(tokens["correlation_id"])
    if "service" in tokens:
        service_var.reset(tokens["service"])

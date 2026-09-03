import json
import logging
from contextvars import ContextVar, Token

logger = logging.getLogger("childhood_haven.observability")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

_request_id: ContextVar[str] = ContextVar("request_id", default="unknown")


def bind_request_id(request_id: str) -> Token:
    return _request_id.set(request_id)


def reset_request_id(token: Token) -> None:
    _request_id.reset(token)


def _emit(event: str, **fields: object) -> None:
    record = {"event": event, "request_id": _request_id.get(), **fields}
    logger.info(json.dumps(record, ensure_ascii=False, separators=(",", ":")))


def log_request(route: str, method: str, status_code: int, duration_ms: float) -> None:
    _emit(
        "request.completed",
        route=route,
        method=method,
        status_code=status_code,
        duration_ms=round(duration_ms, 1),
    )


def log_api_error(route: str, status_code: int, error_type: str) -> None:
    _emit(
        "request.error",
        route=route,
        status_code=status_code,
        error_type=error_type,
    )


def log_agent_node(
    node: str,
    duration_ms: float,
    outcome: str,
    error_type: str | None = None,
) -> None:
    fields: dict[str, object] = {
        "node": node,
        "duration_ms": round(duration_ms, 1),
        "outcome": outcome,
    }
    if error_type is not None:
        fields["error_type"] = error_type
    _emit("agent.node.completed", **fields)

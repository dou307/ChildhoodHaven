from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.observability import log_api_error


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": _request_id(request),
    }
    if details is not None:
        content["details"] = details
    return JSONResponse(status_code=status_code, content=content, headers=headers)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        code = {
            401: "unauthorized",
            404: "not_found",
            409: "conflict",
            422: "unprocessable_request",
        }.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) else "请求未能完成"
        log_api_error(_route_template(request), exc.status_code, type(exc).__name__)
        return _error_response(request, exc.status_code, code, message, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        log_api_error(_route_template(request), 422, type(exc).__name__)
        return _error_response(
            request,
            422,
            "invalid_request",
            "请求参数不符合接口要求",
            details=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        log_api_error(_route_template(request), 500, type(exc).__name__)
        return _error_response(request, 500, "internal_error", "服务暂时不可用，请稍后重试")

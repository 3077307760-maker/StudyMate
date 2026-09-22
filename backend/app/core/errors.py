"""Typed application errors and FastAPI exception handlers."""

import json
from collections.abc import AsyncIterator
from typing import Any, cast
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
        request.state.request_id = request_id
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            body_iterator = cast(AsyncIterator[bytes], response.body_iterator)  # type: ignore[attr-defined]
            body = b"".join([chunk async for chunk in body_iterator])
            try:
                payload = json.loads(body or b"{}")
                if isinstance(payload, dict):
                    payload.setdefault("request_id", request_id)
                response = JSONResponse(
                    status_code=response.status_code,
                    content=payload,
                    headers={
                        key: value
                        for key, value in response.headers.items()
                        if key.lower() not in {"content-length", "content-type", "x-request-id"}
                    },
                )
            except (TypeError, ValueError):
                pass
        response.headers["X-Request-ID"] = request_id
        return response


def _error_response(
    request: Request,
    code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", f"req_{uuid4().hex}")
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": details or {},
        },
        headers={"X-Request-ID": request_id},
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(request, exc.code, exc.message, exc.status_code, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            request,
            "VALIDATION_ERROR",
            "请求参数校验失败。",
            422,
            {"errors": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, _: Exception) -> JSONResponse:
        return _error_response(request, "INTERNAL_ERROR", "服务器内部错误。", 500)

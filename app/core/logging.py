"""Structured logging + request context utilities.

- `configure_logging` installs a JSON formatter when `LOG_JSON` is true,
  plain text otherwise.
- `RequestIdMiddleware` attaches a `request_id` to every request, exposes it
  as an `X-Request-ID` response header, and binds it to the log record via a
  `ContextVar`.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get() or "-"
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(*, level: str = "INFO", json_format: bool = True) -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.addFilter(_RequestIdFilter())
    if json_format:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(request_id)s] "
                "%(name)s: %(message)s"
            )
        )
    root.addHandler(handler)
    root.setLevel(level.upper())


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Bind an `X-Request-ID` per request to logs and response headers."""

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        incoming = request.headers.get(self.header_name)
        request_id = incoming or uuid.uuid4().hex
        token = _request_id_ctx.set(request_id)
        try:
            response: Response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        response.headers[self.header_name] = request_id
        return response

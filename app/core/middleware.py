from __future__ import annotations

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, new_request_id, request_id_var


logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or new_request_id()
        token = request_id_var.set(request_id)

        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        except Exception:
            logger.exception(
                "request_error",
                extra={
                    "method": request.method,
                    "path": str(request.url.path),
                    "client": request.client.host if request.client else None,
                },
            )
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            if response is not None:
                response.headers["X-Request-ID"] = request_id

            # Note: response may not exist in error case; log here anyway.
            logger.info(
                "request_complete",
                extra={
                    "method": request.method,
                    "path": str(request.url.path),
                    "status_code": response.status_code if response is not None else 500,
                    "elapsed_ms": elapsed_ms,
                },
            )
            request_id_var.reset(token)

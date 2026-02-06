"""FastAPI middleware for request tracing and observability."""

import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to every request for tracing.

    - Reads X-Request-ID from request headers, or generates a UUID if missing
    - Binds request_id to structlog context (auto-included in all logs)
    - Adds X-Request-ID to response headers

    Usage:
        app.add_middleware(RequestIDMiddleware)

        # In any endpoint or dependency:
        logger.info("something_happened")  # request_id automatically included
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Use existing request ID or generate new one
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        # Bind to structlog context — all logs in this request will include it
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)

        # Add to response headers for client tracing
        response.headers[REQUEST_ID_HEADER] = request_id

        return response

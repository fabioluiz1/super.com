from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import shutdown
from app.dependencies import DB
from app.exceptions import DomainError, NotFoundError
from app.logging import get_logger
from app.middleware import RequestIDMiddleware
from app.schemas.error import ErrorDetail, ErrorResponse

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager — code before yield runs on startup, after yield on shutdown.

    Startup: initialize caches, warm up connections.
    Shutdown: close database connections gracefully.
    """
    yield
    await shutdown()


app = FastAPI(lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)


def _error_json(code: str, message: str) -> dict[str, object]:
    """Build the standard error envelope as a dict for JSONResponse."""
    return ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump()


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Return 404 with the entity details."""
    return JSONResponse(status_code=404, content=_error_json("not_found", exc.message))


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Return 400 for generic domain-level violations."""
    logger.warning("domain_error", error=exc.message, path=request.url.path)
    return JSONResponse(status_code=400, content=_error_json("domain_error", exc.message))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unhandled exceptions and return a safe error response.

    - Logs full exception with traceback (includes request_id from context)
    - Returns generic error to client (no stack traces leaked)
    """
    logger.exception("unhandled_exception", path=request.url.path, method=request.method)
    return JSONResponse(
        status_code=500,
        content=_error_json("internal_error", "Internal server error"),
    )


@app.get("/health")
async def health(db: DB) -> dict[str, str]:
    """Health check endpoint — verifies database connectivity.

    Returns 200 OK only if the database responds to a ping query.
    Used by load balancers and container orchestrators to detect unhealthy instances.
    """
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}

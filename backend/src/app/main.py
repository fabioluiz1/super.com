from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, shutdown
from app.logging import get_logger
from app.middleware import RequestIDMiddleware

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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unhandled exceptions and return a safe error response.

    - Logs full exception with traceback (includes request_id from context)
    - Returns generic error to client (no stack traces leaked)
    """
    logger.exception("unhandled_exception", path=request.url.path, method=request.method)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Database session type with dependency injection.
#
# Annotated[Type, Metadata] combines two things:
#   - AsyncSession: the type hint (for mypy and IDE autocomplete)
#   - Depends(get_db): tells FastAPI to call get_db() and inject the result
#
# When you write `async def health(db: DB)`, FastAPI:
#   1. Calls get_db() before each request
#   2. Passes the yielded session as the `db` argument
#   3. Closes the session after the response (even if an error occurs)
#
# This is dependency injection — you declare what you need, FastAPI provides it.
DB = Annotated[AsyncSession, Depends(get_db)]


@app.get("/health")
async def health(db: DB) -> dict[str, str]:
    """Health check endpoint — verifies database connectivity.

    Returns 200 OK only if the database responds to a ping query.
    Used by load balancers and container orchestrators to detect unhealthy instances.
    """
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}

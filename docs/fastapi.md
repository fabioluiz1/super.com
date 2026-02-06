# FastAPI

High-performance async web framework built on:

- **Starlette** — ASGI framework (routing, middleware, WebSocket support)
- **Pydantic** — data validation and serialization via type annotations

Alternatives: Flask (sync WSGI, simpler), Django (batteries-included, built-in ORM), Litestar (similar to FastAPI, different design choices).

## ASGI vs WSGI

**WSGI** (Web Server Gateway Interface, 2003) is Python's original web server protocol. It's synchronous — one request occupies one thread for its entire duration. Handles concurrent requests by spawning multiple threads/processes.

**ASGI** (Asynchronous Server Gateway Interface, 2016) is the async successor. Uses `async/await` to release the thread while waiting for I/O (database queries, HTTP calls). One process can handle thousands of concurrent requests without thousands of threads.

```python
# WSGI (Flask) — thread is blocked during the database call
@app.route("/users")
def get_users():
    users = db.query(User).all()  # Thread waits here
    return jsonify(users)

# ASGI (FastAPI) — thread is released during the database call
@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))  # Thread is free to handle other requests
    return result.scalars().all()
```

**uvicorn** is the ASGI server that runs FastAPI apps. It receives HTTP requests and calls your app as an async coroutine. `--reload` watches for file changes (dev only). `--app-dir src` adds `src/` to Python's import path.

## Application Structure ([main.py](../backend/src/app/main.py))

### Lifespan Context Manager

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield               # Code before yield = startup, after yield = shutdown
    await shutdown()     # Close database connections
```

`app = FastAPI(lifespan=lifespan)` — the `lifespan` parameter accepts an async context manager. Code before `yield` runs once on startup (initialize caches, warm connections). Code after `yield` runs once on shutdown (close connections, flush buffers). This replaces the deprecated `@app.on_event("startup")` pattern.

### Global Exception Handler

```python
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", path=request.url.path, method=request.method)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

Catches any unhandled exception, logs the full traceback with request context (including `request_id` from middleware), and returns a generic error. No stack traces leak to the client.

### Dependency Injection

```python
DB = Annotated[AsyncSession, Depends(get_db)]

@app.get("/health")
async def health(db: DB) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
```

`Annotated[Type, Metadata]` combines:

- `AsyncSession` — the type hint (for mypy and IDE autocomplete)
- `Depends(get_db)` — tells FastAPI to call `get_db()` and inject the result

When FastAPI sees `db: DB` in a route function:

1. Calls `get_db()` before the request
2. Passes the yielded session as the `db` argument
3. Closes the session after the response (even on error)

This is dependency injection — you declare what you need, FastAPI provides it.

# Structured Logging

## Why Structured Logs?

Traditional logging outputs plain text:

```
2024-01-15 10:30:45 INFO User logged in from 192.168.1.1
```

Structured logging outputs JSON:

```json
{"event": "user_login", "ip": "192.168.1.1", "user_id": 42, "timestamp": "2024-01-15T10:30:45Z", "level": "info", "request_id": "abc-123"}
```

Plain text requires regex to parse. JSON is machine-readable — log aggregators (Datadog, ELK, CloudWatch) can filter, search, and alert on any field without custom parsing.

## structlog

[structlog](https://www.structlog.org/) is a structured logging library for Python. It wraps the stdlib `logging` module and adds:

- **Key-value pairs** — attach data to log events as keyword arguments
- **Processors** — a pipeline of functions that transform each log event before output
- **Context binding** — attach data once, include it in all subsequent logs automatically

Alternatives: stdlib `logging` with `json` formatter (manual, verbose), `python-json-logger` (simpler but no processor pipeline).

### Processor Pipeline ([logging.py](../backend/src/app/logging.py))

```python
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.contextvars.merge_contextvars,   # Include bound context (request_id, etc.)
        structlog.stdlib.add_log_level,            # Add "level": "info"
        structlog.stdlib.add_logger_name,          # Add "logger": "app.main"
        _add_timestamp,                            # Add "timestamp": "2024-01-15T10:30:45Z"
        structlog.processors.format_exc_info,      # Format exceptions as strings
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
)
```

Each log event passes through every processor in order. Processors add fields, filter events, or transform the output. The final renderer (`JSONRenderer`) converts the dict to a JSON string.

### Usage

```python
from app.logging import get_logger

logger = get_logger(__name__)

logger.info("user_login", user_id=42, ip="192.168.1.1")
# {"event": "user_login", "user_id": 42, "ip": "192.168.1.1", "level": "info", ...}

logger.warning("rate_limited", endpoint="/api/users", attempts=5)
# {"event": "rate_limited", "endpoint": "/api/users", "attempts": 5, "level": "warning", ...}
```

## Request ID Middleware ([middleware.py](../backend/src/app/middleware.py))

Every HTTP request gets a unique ID for distributed tracing.

```python
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

**How it works:**

1. Reads `X-Request-ID` from the incoming request header, or generates a UUID
2. Binds `request_id` to structlog's contextvars — every log call during this request automatically includes it
3. Adds `X-Request-ID` to the response header — the client can use it for support/debugging

### contextvars

`contextvars` is a Python stdlib module (3.7+) for storing per-task data. In async code, each `asyncio.Task` (i.e., each request) gets its own copy. structlog reads from contextvars on every log call, so bound variables like `request_id` appear automatically without passing them as arguments.

### End-to-End Example

```
Client sends: GET /health  (X-Request-ID: abc-123)
  -> Middleware binds request_id = "abc-123"
  -> Endpoint runs, logs:
      {"event": "health_check", "request_id": "abc-123", "level": "info", ...}
  -> If an error occurs:
      {"event": "unhandled_exception", "request_id": "abc-123", "level": "error", ...}
  -> Response includes: X-Request-ID: abc-123
```

Every log during that request has `"request_id": "abc-123"`, making it trivial to find all logs for a single request in a log aggregator.

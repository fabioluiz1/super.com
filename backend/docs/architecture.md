# Layered Architecture

Every endpoint follows four layers. Each layer has one job and only calls the layer directly below it. Dependency injection (`Depends()`) wires them together — it resolves sessions, services, and config before handler code runs.

## Layers

1. **Routers** (`routers/<entity>.py`)
   - Receive HTTP requests and return HTTP responses — the only layer that knows about HTTP verbs, status codes, and query parameters
   - Declare `response_model` on every endpoint so FastAPI validates the output
   - Use explicit status codes: `200` for reads, `201` for creates
   - Wire each router in `main.py` via `app.include_router()`

2. **Services** (`services/<entity>.py`)
   - Contain business logic and orchestrate calls to one or more repositories
   - Raise domain exceptions (e.g., `NotFoundError`, `ConflictError`) — never `HTTPException`
   - Keep services thin; if a service just forwards to a repo, that's fine

3. **Repositories** (`repositories/<entity>.py`)
   - Execute database queries — pure data access with no knowledge of HTTP or business rules
   - Every function takes `AsyncSession` as its first argument and returns model instances (or `None`)
   - Never raise exceptions; return `None` or an empty list and let the service decide

4. **Schemas** (`schemas/<entity>.py`)
   - Define the shape of request and response data as Pydantic models
   - Set `ConfigDict(from_attributes=True)` so schemas can serialize SQLAlchemy models directly
   - Nest related schemas when the API returns joined data (e.g., `HotelInDeal` inside `DealResponse`)

When building CRUD for a new entity, create files bottom-up (schemas → repos → services → routers), then wire the router and add one integration test per endpoint.

## Error Handling

All error responses use the same envelope:

```json
{"error": {"code": "not_found", "message": "Deal with id 42 not found"}}
```

### Domain exceptions (`app.exceptions`)

Services raise domain exceptions to signal business-rule violations. Exception handlers in `main.py` translate them into HTTP responses with the error envelope.

- `DomainError` — base class; caught as 400 with code `"domain_error"`
- `NotFoundError(entity, identifier)` — caught as 404 with code `"not_found"`
- `ConflictError` — for duplicate/conflict scenarios (e.g., unique constraint violations)
- Unhandled `Exception` — caught as 500 with code `"internal_error"`, logged with traceback

### Error schemas (`app.schemas.error`)

- `ErrorDetail` — inner object with `code: str` and `message: str`
- `ErrorResponse` — top-level envelope with `error: ErrorDetail`

Routers never construct error responses directly — they let exceptions propagate to the handlers.

## Shared Dependencies (`app.dependencies`)

- `DB = Annotated[AsyncSession, Depends(get_db)]` — the database session type alias used by all endpoints
- Defined in `dependencies.py` (not `main.py`) to avoid circular imports when routers are registered in main

# Error Handling

All error responses use the same envelope:

```json
{"error": {"code": "not_found", "message": "Book with id 42 not found"}}
```

## Domain exceptions (`app.exceptions`)

Services raise domain exceptions to signal business-rule violations. Exception handlers in `main.py` translate them into HTTP responses with the error envelope.

- `DomainError` — base class; caught as 400 with code `"domain_error"`
- `NotFoundError(entity, identifier)` — caught as 404 with code `"not_found"`
- `ConflictError` — for duplicate/conflict scenarios (e.g., unique constraint violations)
- Unhandled `Exception` — caught as 500 with code `"internal_error"`, logged with traceback

## Error schemas (`app.schemas.error`)

- `ErrorDetail` — inner object with `code: str` and `message: str`
- `ErrorResponse` — top-level envelope with `error: ErrorDetail`

Routers never construct error responses directly — they let exceptions propagate to the handlers.

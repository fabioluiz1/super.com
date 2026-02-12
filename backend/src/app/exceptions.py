"""Domain exceptions raised by services and caught by routers.

Services raise these to signal business-rule violations.
Exception handlers in main.py translate them into the standard
error envelope: {"error": {"code": "...", "message": "..."}}.
"""


class DomainError(Exception):
    """Base class for all domain exceptions."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    """Raised when a requested entity does not exist."""

    def __init__(self, entity: str, identifier: object) -> None:
        self.entity = entity
        self.identifier = identifier
        super().__init__(f"{entity} with id {identifier} not found")


class ConflictError(DomainError):
    """Raised when an operation conflicts with existing state (e.g. duplicate)."""

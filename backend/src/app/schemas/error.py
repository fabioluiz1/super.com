"""Error response schemas.

All error responses use the same envelope: {"error": {"code": "...", "message": "..."}}.
Exception handlers in main.py construct these from domain exceptions.
"""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Inner error object with a machine-readable code and human-readable message."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Top-level error envelope returned by all error responses."""

    error: ErrorDetail

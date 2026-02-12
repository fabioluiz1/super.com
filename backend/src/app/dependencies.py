"""Shared FastAPI dependencies.

Reusable type aliases and dependency functions that routers import.
Defined here (not in main.py) to avoid circular imports when routers
are registered in main.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

DB = Annotated[AsyncSession, Depends(get_db)]

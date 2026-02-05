from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Pydantic Settings automatically reads env vars matching field names (case-insensitive).
    In development, it also reads from .env file if present.
    In production, set environment variables directly (Docker, k8s, etc.).
    """

    # Database connection URL
    # Format: postgresql+asyncpg://user:password@host:port/database
    # - postgresql = SQLAlchemy dialect
    # - asyncpg = async driver (high-performance, Cython-based)
    database_url: str = "postgresql+asyncpg://super@localhost:5432/super"

    # Connection pool settings (see docs/database.md for details)
    # These tune how SQLAlchemy manages database connections.
    db_pool_size: int = 5  # Number of persistent connections to keep open
    db_max_overflow: int = 10  # Extra connections allowed beyond pool_size under load
    db_pool_timeout: int = 30  # Seconds to wait for available connection before error
    db_pool_recycle: int = 3600  # Recreate connections older than this (seconds)
    db_pool_pre_ping: bool = True  # Test connection with SELECT 1 before using
    db_echo: bool = False  # Log all SQL statements (True for debugging)
    db_statement_timeout: int = 30  # Max seconds for a query before it's killed

    model_config = SettingsConfigDict(
        env_file=".env",  # Load from .env in development
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars
    )


settings = Settings()

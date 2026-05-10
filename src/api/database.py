from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
from sqlmodel import create_engine, Session

@dataclass(frozen=True)
class DatabaseSettings:
    url: str | None

    @property
    def configured(self) -> bool:
        return bool(self.url)

    @property
    def safe_url(self) -> str | None:
        if not self.url:
            return None

        parsed = urlsplit(self.url)
        if "@" not in parsed.netloc:
            return self.url

        credentials, host = parsed.netloc.rsplit("@", 1)
        user = credentials.split(":", 1)[0]
        return urlunsplit(parsed._replace(netloc=f"{user}:***@{host}"))

def load_database_settings() -> DatabaseSettings:
    return DatabaseSettings(url=os.getenv("DATABASE_URL"))

def get_engine():
    settings = load_database_settings()
    if settings.configured:
        # Avoid asyncpg if we are using psycopg2 in requirements
        url = settings.url.replace("postgres://", "postgresql://")
        return create_engine(url, pool_pre_ping=True)
    return None

def database_status(settings: DatabaseSettings | None = None) -> dict:
    db_settings = settings or load_database_settings()
    if not db_settings.configured:
        return {
            "name": "database",
            "status": "not_configured",
            "detail": "DATABASE_URL is not set; using local processed CSV artifacts.",
            "metadata": {"url": None},
        }

    # Ping the db to verify connection
    status = "configured"
    detail = "DATABASE_URL is configured for the live TimescaleDB service."
    try:
        from sqlalchemy import text
        engine = get_engine()
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        status = "online"
        detail = "TimescaleDB connection verified."
    except Exception as e:
        status = "error"
        detail = f"Database connection failed: {str(e)}"

    return {
        "name": "database",
        "status": status,
        "detail": detail,
        "metadata": {"url": db_settings.safe_url},
    }

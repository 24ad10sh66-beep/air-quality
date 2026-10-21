"""Safe MySQL connection helpers."""

from __future__ import annotations

import os
import ssl
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def load_environment(root: Path) -> None:
    """Load local environment values without printing secrets."""
    load_dotenv(root / ".env", override=False)


def build_database_url(include_database: bool = True) -> str:
    """Build a SQLAlchemy URL while safely escaping credentials."""
    required = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD")
    missing = [name for name in required if not os.getenv(name)]
    if include_database:
        missing.extend(
            name for name in ("DB_NAME",) if not os.getenv(name)
        )
    if missing:
        raise RuntimeError(
            "Missing database configuration: " + ", ".join(sorted(set(missing)))
        )
    database = os.getenv("DB_NAME", "") if include_database else ""
    suffix = f"/{quote_plus(database)}" if database else ""
    return (
        f"mysql+pymysql://{quote_plus(os.environ['DB_USER'])}:"
        f"{quote_plus(os.environ['DB_PASSWORD'])}@"
        f"{os.environ['DB_HOST']}:{os.environ['DB_PORT']}{suffix}"
        "?charset=utf8mb4"
    )


def create_database_engine(include_database: bool = True) -> Engine:
    """Create an engine with bounded connection and pool settings."""
    return create_engine(
        build_database_url(include_database=include_database),
        connect_args={
            "connect_timeout": 10,
            "ssl": {
                "ca": str(
                    Path(__file__).resolve().parents[3]
                    / "certs"
                    / "aiven-ca.pem"
                )
            },
        },
        pool_pre_ping=True,
        pool_recycle=1800,
    )


def check_connection(engine: Engine) -> str:
    """Return the server version after a safe read-only health check."""
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT VERSION()")).scalar_one())

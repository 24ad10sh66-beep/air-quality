"""Run a non-destructive MySQL connectivity check."""

from pathlib import Path

from air_quality.db.connection import (
    check_connection,
    create_database_engine,
    load_environment,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    load_environment(ROOT)
    try:
        engine = create_database_engine()
        version = check_connection(engine)
    except Exception as exc:
        raise SystemExit(f"Database health check failed: {exc}") from exc
    print(f"MySQL connection succeeded; server version: {version}")


if __name__ == "__main__":
    main()

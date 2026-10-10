"""Create the configured MySQL database without modifying existing databases."""

from pathlib import Path

from sqlalchemy import text

from air_quality.db.connection import (
    create_database_engine,
    load_environment,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    load_environment(ROOT)
    database_name = __import__("os").environ["DB_NAME"]
    engine = create_database_engine(include_database=False)
    statement = text(
        f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    with engine.begin() as connection:
        connection.execute(statement)
    print(f"Database is ready: {database_name}")


if __name__ == "__main__":
    main()

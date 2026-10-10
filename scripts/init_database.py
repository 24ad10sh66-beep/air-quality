"""Apply the non-destructive initial schema to a configured database."""

from pathlib import Path

from sqlalchemy import text

from air_quality.db.connection import create_database_engine, load_environment


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "database" / "schema" / "001_initial_schema.sql"


def main() -> None:
    load_environment(ROOT)
    if not SCHEMA_PATH.exists():
        raise SystemExit(f"Schema file not found: {SCHEMA_PATH}")
    sql_without_comments = "\n".join(
        line
        for line in SCHEMA_PATH.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    )
    statements = [
        statement.strip()
        for statement in sql_without_comments.split(";")
        if statement.strip()
    ]
    engine = create_database_engine()
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    print(f"Applied {len(statements)} non-destructive schema statements.")


if __name__ == "__main__":
    main()

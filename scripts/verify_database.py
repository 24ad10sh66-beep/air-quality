"""Verify imported row counts and basic database integrity."""

from pathlib import Path

from sqlalchemy import text

from air_quality.db.connection import create_database_engine, load_environment


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROWS = 382_343


def main() -> None:
    load_environment(ROOT)
    engine = create_database_engine()
    with engine.connect() as connection:
        readings = connection.execute(
            text("SELECT COUNT(*) FROM air_quality_readings")
        ).scalar_one()
        batches = connection.execute(
            text(
                "SELECT COUNT(*), COALESCE(SUM(inserted_rows), 0) "
                "FROM import_batches WHERE status='completed'"
            )
        ).one()
        timestamps = connection.execute(
            text(
                "SELECT MIN(observed_at), MAX(observed_at), "
                "COUNT(DISTINCT city) FROM air_quality_readings"
            )
        ).one()
    if readings != EXPECTED_ROWS:
        raise SystemExit(
            f"Database verification failed: expected {EXPECTED_ROWS:,}, "
            f"found {readings:,} readings."
        )
    print(
        f"Database verification passed: {readings:,} readings; "
        f"{batches[0]} completed batch; inserted total {batches[1]:,}; "
        f"observed_at range {timestamps[0]} to {timestamps[1]}; "
        f"{timestamps[2]} cities."
    )


if __name__ == "__main__":
    main()

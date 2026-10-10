"""Import the validated clean CSV into MySQL in repeat-safe batches."""

from __future__ import annotations

import csv
import hashlib
import os
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from air_quality.db.connection import create_database_engine, load_environment


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "bulk_combined_dataset_clean.csv"
REPORT = ROOT / "data" / "reports" / "database_import_report.md"
CHUNK_SIZE = 2_000
TARGET_COLUMNS = (
    "city", "observed_at", "pm2_5", "pm10", "no_value", "no2", "nox",
    "nh3", "co", "so2", "o3", "benzene", "toluene", "xylene", "aqi",
    "aqi_bucket", "source_date", "station", "source_row_number",
    "import_batch_id",
)


def optional_float(value: str) -> float | None:
    return float(value) if value else None


def optional_datetime(value: str) -> str | None:
    if not value:
        return None
    return value


def optional_date(value: str) -> str | None:
    if not value:
        return None
    return datetime.strptime(value, "%d/%m/%y").date().isoformat()


def main() -> None:
    load_environment(ROOT)
    if not SOURCE.exists():
        raise SystemExit(f"Clean dataset not found: {SOURCE}")
    source_sha256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    batch_id = str(uuid.uuid4())
    engine = create_database_engine()

    with engine.begin() as connection:
        existing = connection.execute(
            text(
                "SELECT id, status, inserted_rows FROM import_batches "
                "WHERE source_sha256 = :checksum"
            ),
            {"checksum": source_sha256},
        ).mappings().first()
        if existing is not None and existing["status"] == "completed":
            print(
                "Import already completed for this clean-file checksum: "
                f"{existing['inserted_rows']:,} rows."
            )
            return
        connection.execute(
            text(
                "INSERT INTO import_batches "
                "(id, source_path, source_sha256, attempted_rows, inserted_rows, "
                "rejected_rows, status, started_at) "
                "VALUES (:id, :path, :checksum, 0, 0, 0, 'running', :started)"
            ),
            {
                "id": batch_id,
                "path": str(SOURCE),
                "checksum": source_sha256,
                "started": datetime.now(),
            },
        )

    insert_sql = text(
        "INSERT INTO air_quality_readings ("
        + ", ".join(TARGET_COLUMNS)
        + ") VALUES ("
        + ", ".join(f":{column}" for column in TARGET_COLUMNS)
        + ")"
    )
    attempted = inserted = 0
    started = datetime.now()
    try:
        with SOURCE.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            with engine.begin() as connection:
                batch = []
                for source_row, row in enumerate(reader, start=2):
                    attempted += 1
                    batch.append(
                        {
                            "city": row["city"],
                            "observed_at": optional_datetime(row["datetime"]),
                            "pm2_5": optional_float(row["pm2_5"]),
                            "pm10": optional_float(row["pm10"]),
                            "no_value": optional_float(row["no"]),
                            "no2": optional_float(row["no2"]),
                            "nox": optional_float(row["nox"]),
                            "nh3": optional_float(row["nh3"]),
                            "co": optional_float(row["co"]),
                            "so2": optional_float(row["so2"]),
                            "o3": optional_float(row["o3"]),
                            "benzene": optional_float(row["benzene"]),
                            "toluene": optional_float(row["toluene"]),
                            "xylene": optional_float(row["xylene"]),
                            "aqi": optional_float(row["aqi"]),
                            "aqi_bucket": row["aqi_bucket"] or None,
                            "source_date": optional_date(row["date"]),
                            "station": row["station"] or None,
                            "source_row_number": source_row,
                            "import_batch_id": batch_id,
                        }
                    )
                    if len(batch) >= CHUNK_SIZE:
                        connection.execute(insert_sql, batch)
                        inserted += len(batch)
                        batch.clear()
                if batch:
                    connection.execute(insert_sql, batch)
                    inserted += len(batch)
                connection.execute(
                    text(
                        "UPDATE import_batches SET attempted_rows=:attempted, "
                        "inserted_rows=:inserted, status='completed', "
                        "completed_at=:completed WHERE id=:id"
                    ),
                    {
                        "attempted": attempted,
                        "inserted": inserted,
                        "completed": datetime.now(),
                        "id": batch_id,
                    },
                )
    except Exception:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE import_batches SET attempted_rows=:attempted, "
                    "inserted_rows=0, status='failed', completed_at=:completed "
                    "WHERE id=:id"
                ),
                {"attempted": attempted, "completed": datetime.now(), "id": batch_id},
            )
        raise

    REPORT.write_text(
        "\n".join(
            [
                "# Database import report",
                "",
                f"- Source: `{SOURCE}`",
                f"- Source SHA-256: `{source_sha256}`",
                f"- Database: `{os.environ['DB_NAME']}`",
                "- Table: `air_quality_readings`",
                f"- Import batch: `{batch_id}`",
                f"- Attempted rows: `{attempted:,}`",
                f"- Inserted rows: `{inserted:,}`",
                "- Rejected rows: `0`",
                "- Status: `completed`",
                f"- Started: `{started.isoformat()}`",
                f"- Completed: `{datetime.now().isoformat()}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Imported {inserted:,} rows in batch {batch_id}.")


if __name__ == "__main__":
    main()

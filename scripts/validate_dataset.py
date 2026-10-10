"""Validate the generated clean CSV and its cleaning audit."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    clean_path = ROOT / "data" / "processed" / "bulk_combined_dataset_clean.csv"
    report_path = ROOT / "data" / "reports" / "cleaning_report.json"
    if not clean_path.exists():
        raise FileNotFoundError(f"Clean dataset not found: {clean_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    with clean_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        header = next(reader, None)
        if not header:
            raise ValueError("Clean dataset has no header")
        rows = sum(1 for _ in reader)
    if len(header) != len(set(header)):
        raise ValueError("Clean dataset has duplicate standardized headers")
    if rows != report["rows_clean"]:
        raise ValueError(
            f"Clean row count {rows} does not match report {report['rows_clean']}"
        )
    print(f"Validation passed: {rows:,} rows, {len(header)} columns.")


if __name__ == "__main__":
    main()

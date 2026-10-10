"""Conservative, auditable CSV cleaning for the air-quality dataset."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable


MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", "missing"}
NUMERIC_COLUMNS = {
    "PM2.5",
    "PM10",
    "NO",
    "NO2",
    "NOx",
    "NH3",
    "CO",
    "SO2",
    "O3",
    "Benzene",
    "Toluene",
    "Xylene",
    "AQI",
}
DATE_FORMATS = {
    "Datetime": ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"),
    "Date": ("%d/%m/%y",),
}


def standardize_column_name(name: str) -> str:
    """Convert an observed header to a stable snake_case name."""
    value = name.strip()
    value = value.replace("%", " percent ")
    value = re.sub(r"[^0-9A-Za-z]+", "_", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"_+", "_", value).strip("_").lower()
    if not value:
        raise ValueError("A column name becomes empty after standardization")
    if value[0].isdigit():
        value = f"column_{value}"
    return value


def normalize_value(value: str) -> str:
    """Trim values and represent configured missing tokens as empty CSV cells."""
    trimmed = value.strip()
    return "" if trimmed.lower() in MISSING_TOKENS else trimmed


def _parse_date(value: str, formats: Iterable[str]) -> bool:
    return any(_try_parse_date(value, fmt) for fmt in formats)


def _try_parse_date(value: str, fmt: str) -> bool:
    try:
        datetime.strptime(value, fmt)
    except ValueError:
        return False
    return True


def _is_valid_number(value: str) -> bool:
    try:
        parsed = float(value)
    except ValueError:
        return False
    return math.isfinite(parsed)


@dataclass
class CleaningSummary:
    source_path: str
    output_path: str
    rejected_path: str
    source_sha256: str
    rows_read: int
    rows_clean: int
    rows_rejected: int
    rejection_reasons: dict[str, int]
    full_duplicate_rows_removed: int
    missing_values_normalized: int
    numeric_conversion_failures: int
    date_conversion_failures: int
    field_count_failures: int
    original_headers: list[str]
    standardized_headers: list[str]


def clean_dataset(
    source_path: Path,
    output_path: Path,
    rejected_path: Path,
    report_path: Path,
) -> CleaningSummary:
    """Clean a CSV without mutating its source and write an audit report."""
    source_bytes = source_path.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rejected_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    reasons: Counter[str] = Counter()
    seen_rows: set[str] = set()
    rows_read = rows_clean = rows_rejected = 0
    missing_normalized = numeric_failures = date_failures = field_failures = 0

    with (
        source_path.open("r", encoding="utf-8-sig", newline="") as source,
        output_path.open("w", encoding="utf-8", newline="") as clean_file,
        rejected_path.open("w", encoding="utf-8", newline="") as rejected_file,
    ):
        reader = csv.reader(source)
        try:
            original_headers = next(reader)
        except StopIteration as exc:
            raise ValueError("The source CSV is empty") from exc

        original_headers = [header.strip() for header in original_headers]
        standardized_headers = [
            standardize_column_name(header) for header in original_headers
        ]
        if len(set(standardized_headers)) != len(standardized_headers):
            raise ValueError(
                "Standardized headers collide; refusing to discard duplicate columns"
            )

        clean_writer = csv.writer(clean_file)
        rejected_writer = csv.writer(rejected_file)
        clean_writer.writerow(standardized_headers)
        rejected_writer.writerow(["source_row", "reason", *original_headers])

        for source_row, row in enumerate(reader, start=2):
            rows_read += 1
            reason: str | None = None
            if len(row) != len(original_headers):
                field_failures += 1
                reason = "field_count_mismatch"
            values = [normalize_value(value) for value in row]
            missing_normalized += sum(
                original.strip().lower() in MISSING_TOKENS and original.strip() != ""
                for original in row
            )

            if reason is None:
                observed = dict(zip(original_headers, values))
                for column in NUMERIC_COLUMNS:
                    value = observed.get(column, "")
                    if value and not _is_valid_number(value):
                        numeric_failures += 1
                        reason = f"invalid_numeric:{column}"
                        break
                if reason is None:
                    for column, formats in DATE_FORMATS.items():
                        value = observed.get(column, "")
                        if value and not _parse_date(value, formats):
                            date_failures += 1
                            reason = f"invalid_date:{column}"
                            break

            row_hash = hashlib.sha1(
                "\x1f".join(values).encode("utf-8")
            ).hexdigest()
            if reason is None and row_hash in seen_rows:
                reasons["duplicate_full_row"] += 1
                rows_rejected += 1
                rejected_writer.writerow([source_row, "duplicate_full_row", *row])
                continue
            seen_rows.add(row_hash)

            if reason is not None:
                reasons[reason] += 1
                rows_rejected += 1
                rejected_writer.writerow([source_row, reason, *row])
                continue

            clean_writer.writerow(values)
            rows_clean += 1

    summary = CleaningSummary(
        source_path=str(source_path),
        output_path=str(output_path),
        rejected_path=str(rejected_path),
        source_sha256=source_sha256,
        rows_read=rows_read,
        rows_clean=rows_clean,
        rows_rejected=rows_rejected,
        rejection_reasons=dict(sorted(reasons.items())),
        full_duplicate_rows_removed=reasons.get("duplicate_full_row", 0),
        missing_values_normalized=missing_normalized,
        numeric_conversion_failures=numeric_failures,
        date_conversion_failures=date_failures,
        field_count_failures=field_failures,
        original_headers=original_headers,
        standardized_headers=standardized_headers,
    )
    report_path.write_text(
        json.dumps(asdict(summary), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    markdown = [
        "# Cleaning report",
        "",
        f"- Source: `{summary.source_path}`",
        f"- Source SHA-256: `{summary.source_sha256}`",
        f"- Clean output: `{summary.output_path}`",
        f"- Rejected output: `{summary.rejected_path}`",
        f"- Rows read: `{summary.rows_read:,}`",
        f"- Clean rows: `{summary.rows_clean:,}`",
        f"- Rejected rows: `{summary.rows_rejected:,}`",
        f"- Full duplicate rows removed: `{summary.full_duplicate_rows_removed:,}`",
        f"- Missing values normalized: `{summary.missing_values_normalized:,}`",
        f"- Numeric conversion failures: `{summary.numeric_conversion_failures:,}`",
        f"- Date conversion failures: `{summary.date_conversion_failures:,}`",
        f"- Field-count failures: `{summary.field_count_failures:,}`",
        "",
        "## Rejection reasons",
        "",
        "| Reason | Count |",
        "|---|---:|",
    ]
    markdown.extend(
        f"| `{reason}` | {count:,} |"
        for reason, count in summary.rejection_reasons.items()
    )
    report_path.with_suffix(".md").write_text(
        "\n".join(markdown) + "\n",
        encoding="utf-8",
    )
    return summary

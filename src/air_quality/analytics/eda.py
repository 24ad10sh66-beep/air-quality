"""Database-backed exploratory analysis without modifying source data."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


POLLUTANTS = (
    "pm2_5", "pm10", "no_value", "no2", "nox", "nh3", "co", "so2",
    "o3", "benzene", "toluene", "xylene", "aqi",
)


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _rows(result: Any) -> list[dict[str, Any]]:
    return [
        {key: _json_value(value) for key, value in row.items()}
        for row in result.mappings()
    ]


def run_eda(engine: Engine, report_path: Path) -> dict[str, Any]:
    """Run descriptive SQL analysis and write a JSON report."""
    with engine.connect() as connection:
        overview = _rows(connection.execute(text(
            "SELECT COUNT(*) AS rows_total, COUNT(observed_at) AS timestamp_rows, "
            "MIN(observed_at) AS min_observed_at, MAX(observed_at) AS max_observed_at, "
            "COUNT(DISTINCT city) AS cities, COUNT(DISTINCT station) AS stations "
            "FROM air_quality_readings"
        )))[0]
        city_counts = _rows(connection.execute(text(
            "SELECT city, COUNT(*) AS rows_total, COUNT(observed_at) AS timestamp_rows, "
            "AVG(aqi) AS aqi_mean, MIN(aqi) AS aqi_min, MAX(aqi) AS aqi_max "
            "FROM air_quality_readings GROUP BY city ORDER BY city"
        )))
        bucket_counts = _rows(connection.execute(text(
            "SELECT COALESCE(aqi_bucket, '[missing]') AS aqi_bucket, COUNT(*) AS rows_total "
            "FROM air_quality_readings GROUP BY aqi_bucket ORDER BY rows_total DESC"
        )))
        yearly = _rows(connection.execute(text(
            "SELECT YEAR(observed_at) AS year, COUNT(*) AS rows_total, "
            "AVG(aqi) AS aqi_mean, MIN(aqi) AS aqi_min, MAX(aqi) AS aqi_max "
            "FROM air_quality_readings WHERE observed_at IS NOT NULL "
            "GROUP BY YEAR(observed_at) ORDER BY year"
        )))
        null_counts = _rows(connection.execute(text(
            "SELECT COUNT(*) - COUNT(observed_at) AS observed_at_nulls, "
            "COUNT(*) - COUNT(pm2_5) AS pm2_5_nulls, "
            "COUNT(*) - COUNT(pm10) AS pm10_nulls, "
            "COUNT(*) - COUNT(no_value) AS no_nulls, "
            "COUNT(*) - COUNT(no2) AS no2_nulls, "
            "COUNT(*) - COUNT(nox) AS nox_nulls, "
            "COUNT(*) - COUNT(nh3) AS nh3_nulls, "
            "COUNT(*) - COUNT(co) AS co_nulls, "
            "COUNT(*) - COUNT(so2) AS so2_nulls, "
            "COUNT(*) - COUNT(o3) AS o3_nulls, "
            "COUNT(*) - COUNT(benzene) AS benzene_nulls, "
            "COUNT(*) - COUNT(toluene) AS toluene_nulls, "
            "COUNT(*) - COUNT(xylene) AS xylene_nulls, "
            "COUNT(*) - COUNT(aqi) AS aqi_nulls, "
            "COUNT(*) - COUNT(aqi_bucket) AS aqi_bucket_nulls, "
            "COUNT(*) - COUNT(source_date) AS source_date_nulls, "
            "COUNT(*) - COUNT(station) AS station_nulls "
            "FROM air_quality_readings"
        )))[0]
        pollutant_stats: dict[str, dict[str, Any]] = {}
        for column in POLLUTANTS:
            pollutant_stats[column] = _rows(connection.execute(text(
                f"SELECT COUNT({column}) AS non_null, AVG({column}) AS mean, "
                f"MIN({column}) AS min_value, MAX({column}) AS max_value "
                f"FROM air_quality_readings"
            )))[0]

    report = {
        "scope": "descriptive EDA from verified air_quality_readings table",
        "model_training_performed": False,
        "overview": overview,
        "city_counts": city_counts,
        "aqi_bucket_counts": bucket_counts,
        "yearly_aqi_summary": yearly,
        "null_counts": null_counts,
        "pollutant_stats": pollutant_stats,
        "limitations": [
            "Correlation and causal analysis are not inferred from these aggregates.",
            "Rows without observed_at are excluded from yearly time summaries.",
            "Station is sparse and is not used as a complete geographic key.",
            "No target, feature set, split, or model was created in this phase.",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report

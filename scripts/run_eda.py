"""Run read-only exploratory analysis against the verified MySQL dataset."""

from pathlib import Path

from air_quality.analytics.eda import run_eda
from air_quality.db.connection import create_database_engine, load_environment


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    load_environment(ROOT)
    report = run_eda(
        create_database_engine(),
        ROOT / "data" / "reports" / "eda_report.json",
    )
    overview = report["overview"]
    print(
        f"EDA complete: {overview['rows_total']:,} rows, "
        f"{overview['cities']} cities, "
        f"{overview['min_observed_at']} to {overview['max_observed_at']}."
    )
    print("Model training performed: False")


if __name__ == "__main__":
    main()

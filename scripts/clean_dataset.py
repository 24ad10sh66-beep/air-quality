"""Run the repeatable air-quality CSV cleaning pipeline."""

from pathlib import Path

from air_quality.data.cleaning import clean_dataset


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    summary = clean_dataset(
        source_path=ROOT / "data" / "raw" / "bulk_combined_dataset.csv",
        output_path=ROOT / "data" / "processed" / "bulk_combined_dataset_clean.csv",
        rejected_path=ROOT / "data" / "rejected" / "bulk_combined_dataset_rejected.csv",
        report_path=ROOT / "data" / "reports" / "cleaning_report.json",
    )
    print(
        f"Cleaned {summary.rows_clean:,} rows; "
        f"rejected {summary.rows_rejected:,} rows."
    )


if __name__ == "__main__":
    main()

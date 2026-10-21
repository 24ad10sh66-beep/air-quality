"""Train forecasting and anomaly models and save reproducible artifacts."""

from pathlib import Path

from air_quality.models.time_series import train


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    result = train(
        ROOT / "data" / "processed" / "bulk_combined_dataset_clean.csv",
        ROOT / "artifacts" / "models",
    )
    print(f"Trained {len(result.metrics['targets'])} targets.")
    print(f"Saved {len(result.forecasts)} forecast points and {len(result.anomalies)} anomalies.")


if __name__ == "__main__":
    main()

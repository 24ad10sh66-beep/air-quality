"""Leakage-safe time-series training and anomaly detection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, IsolationForest
from sklearn.metrics import mean_absolute_error, mean_squared_error

TARGETS = [
    "aqi",
    "pm2_5",
    "pm10",
    "no2",
    "so2",
    "o3",
    "co",
    "no",
    "nox",
    "nh3",
    "benzene",
    "toluene",
    "xylene",
]
LAGS = (1, 2, 3, 6, 12, 24, 48, 168)
HORIZON = 48


@dataclass(frozen=True)
class TrainingResult:
    metrics: dict[str, Any]
    forecasts: list[dict[str, Any]]
    anomalies: list[dict[str, Any]]


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _features(frame: pd.DataFrame, target: str) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    timestamp = frame["observed_at"]
    result["hour"] = timestamp.dt.hour
    result["day_of_week"] = timestamp.dt.dayofweek
    result["day_of_year"] = timestamp.dt.dayofyear
    result["month"] = timestamp.dt.month
    for lag in LAGS:
        result[f"lag_{lag}"] = frame[target].shift(lag)
    return result


def _load_data(input_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(input_path)
    frame = frame.rename(columns={"datetime": "observed_at"})
    frame["observed_at"] = pd.to_datetime(frame["observed_at"], errors="coerce")
    frame = frame.dropna(subset=["city", "observed_at"]).sort_values(["city", "observed_at"])
    for target in TARGETS:
        if target not in frame:
            frame[target] = np.nan
        frame[target] = pd.to_numeric(frame[target], errors="coerce")
    return frame.reset_index(drop=True)


def _fit_target(frame: pd.DataFrame, target: str, artifact_dir: Path) -> dict[str, Any]:
    rows: list[pd.DataFrame] = []
    for _, city_frame in frame.groupby("city", sort=False):
        features = _features(city_frame, target)
        features["target"] = city_frame[target].to_numpy()
        features["city"] = city_frame["city"].to_numpy()
        features["observed_at"] = city_frame["observed_at"].to_numpy()
        rows.append(features.dropna(subset=["target"]))
    prepared = pd.concat(rows, ignore_index=True).dropna()
    if len(prepared) < 200:
        raise RuntimeError(f"Not enough usable rows to train {target}: {len(prepared)}")
    prepared = prepared.sort_values("observed_at")
    split = max(int(len(prepared) * 0.8), 1)
    feature_columns = [column for column in prepared.columns if column not in {"target", "city", "observed_at"}]
    train = prepared.iloc[:split]
    test = prepared.iloc[split:]
    model = ExtraTreesRegressor(
        n_estimators=80,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(train[feature_columns], train["target"])
    predictions = model.predict(test[feature_columns])
    metrics = {
        "rows": len(prepared),
        "train_rows": len(train),
        "test_rows": len(test),
        "mae": float(mean_absolute_error(test["target"], predictions)),
        "rmse": float(mean_squared_error(test["target"], predictions) ** 0.5),
        "test_start": test["observed_at"].min().isoformat(),
        "test_end": test["observed_at"].max().isoformat(),
    }
    joblib.dump(
        {"model": model, "feature_columns": feature_columns, "target": target},
        artifact_dir / f"{target}.joblib",
    )
    return metrics


def _forecast_target(frame: pd.DataFrame, target: str, artifact_dir: Path) -> list[dict[str, Any]]:
    bundle = joblib.load(artifact_dir / f"{target}.joblib")
    model = bundle["model"]
    feature_columns = bundle["feature_columns"]
    forecasts: list[dict[str, Any]] = []
    for city, city_frame in frame.groupby("city", sort=False):
        history = city_frame[["observed_at", target]].dropna().sort_values("observed_at").copy()
        if len(history) < max(LAGS):
            continue
        history["observed_at"] = pd.to_datetime(history["observed_at"])
        values = history[target].astype(float).tolist()
        last_time = history["observed_at"].iloc[-1]
        for step in range(1, HORIZON + 1):
            timestamp = last_time + pd.Timedelta(hours=step)
            row: dict[str, float] = {
                "hour": timestamp.hour,
                "day_of_week": timestamp.dayofweek,
                "day_of_year": timestamp.dayofyear,
                "month": timestamp.month,
            }
            for lag in LAGS:
                row[f"lag_{lag}"] = values[-lag]
            prediction = max(float(model.predict(pd.DataFrame([row])[feature_columns])[0]), 0.0)
            values.append(prediction)
            forecasts.append(
                {
                    "city": city,
                    "target": target,
                    "target_time": timestamp.isoformat(),
                    "prediction": prediction,
                    "step": step,
                }
            )
    return forecasts


def _detect_anomalies(frame: pd.DataFrame) -> list[dict[str, Any]]:
    columns = ["aqi", "pm2_5", "pm10", "no2", "so2", "o3", "co"]
    usable = frame[["city", "observed_at", *columns]].dropna().copy()
    if usable.empty:
        return []
    values = usable[columns].to_numpy()
    iso = IsolationForest(contamination=0.01, random_state=42, n_jobs=-1)
    iso_labels = iso.fit_predict(values)
    iso_scores = -iso.score_samples(values)
    rolling = usable.groupby("city", sort=False)[columns].transform(
        lambda values: (values - values.rolling(24, min_periods=6).mean()) /
        values.rolling(24, min_periods=6).std().replace(0, np.nan)
    )
    z_scores = rolling.abs().max(axis=1).fillna(0.0)
    results: list[dict[str, Any]] = []
    for index, row in usable.loc[(iso_labels == -1) | (z_scores >= 3.0)].iterrows():
        methods = []
        position = usable.index.get_loc(index)
        if iso_labels[position] == -1:
            methods.append("isolation_forest")
        if z_scores.loc[index] >= 3.0:
            methods.append("rolling_zscore")
        results.append(
            {
                "city": row["city"],
                "observed_at": row["observed_at"].isoformat(),
                "methods": methods,
                "score": float(max(iso_scores[position], z_scores.loc[index] / 3.0)),
                "aqi": float(row["aqi"]),
            }
        )
    return [{key: value for key, value in item.items() if value is not None} for item in results[-1000:]]


def train(input_path: Path, artifact_dir: Path) -> TrainingResult:
    """Train all configured targets and persist models, metrics, forecasts, and anomalies."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    frame = _load_data(input_path)
    metrics: dict[str, Any] = {
        "dataset": str(input_path),
        "dataset_checksum": _checksum(input_path),
        "horizon_hours": HORIZON,
        "targets": {},
    }
    for target in TARGETS:
        metrics["targets"][target] = _fit_target(frame, target, artifact_dir)
    forecasts: list[dict[str, Any]] = []
    for target in TARGETS:
        forecasts.extend(_forecast_target(frame, target, artifact_dir))
    anomalies = _detect_anomalies(frame)
    (artifact_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (artifact_dir / "forecasts.json").write_text(json.dumps(forecasts, indent=2), encoding="utf-8")
    (artifact_dir / "anomalies.json").write_text(json.dumps(anomalies, indent=2), encoding="utf-8")
    (artifact_dir / "metadata.json").write_text(
        json.dumps({"model": "ExtraTrees autoregressive", "targets": TARGETS, "horizon_hours": HORIZON}, indent=2),
        encoding="utf-8",
    )
    return TrainingResult(metrics=metrics, forecasts=forecasts, anomalies=anomalies)

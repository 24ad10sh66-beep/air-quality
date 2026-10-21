"""FastAPI application for verified historical air-quality data."""

from __future__ import annotations

import json
import os
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.engine import Engine

from air_quality.api.schemas import (
    AnalyticsResponse,
    AnomalyResponse,
    ForecastResponse,
    HealthResponse,
    LiveAqiResponse,
    LocationReportResponse,
    LocationSearchResponse,
    PaginatedReadings,
    SummaryResponse,
)
from air_quality.db.connection import create_database_engine, load_environment

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = ROOT / "artifacts" / "models"
engine: Engine | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global engine
    load_environment(ROOT)
    engine = create_database_engine()
    yield
    if engine is not None:
        engine.dispose()


app = FastAPI(
    title="Air Quality Intelligence API",
    version="0.1.0",
    description="Verified historical air-quality analytics with forecast and anomaly results.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_engine() -> Engine:
    if engine is None:
        raise HTTPException(status_code=503, detail="Database is not initialized")
    return engine


def _numeric(value: Any) -> float | None:
    return float(value) if value is not None else None


def _artifact(name: str, *, required: bool = True) -> list[dict[str, Any]]:
    path = ARTIFACT_DIR / name
    if not path.exists():
        if not required:
            return []
        raise HTTPException(status_code=503, detail=f"Model artifact is not available: {name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail=f"Model artifact cannot be read: {name}") from exc
    if not isinstance(value, list):
        raise HTTPException(status_code=503, detail=f"Invalid model artifact: {name}")
    return value


def _aqi_bucket(aqi: float | None) -> str | None:
    if aqi is None:
        return None
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Satisfactory"
    if aqi <= 200:
        return "Moderate"
    if aqi <= 300:
        return "Poor"
    if aqi <= 400:
        return "Very Poor"
    return "Severe"


def _fetch_openweather(lat: float, lon: float) -> dict[str, Any]:
    token = os.getenv("OPENWEATHER_API_KEY")
    if not token:
        raise HTTPException(
            status_code=503,
            detail="Live AQI is not configured. Add OPENWEATHER_API_KEY to .env.",
        )
    request = Request(
        f"https://api.openweathermap.org/data/2.5/air_pollution"
        f"?lat={lat}&lon={lon}&appid={quote(token)}",
        headers={"Accept": "application/json", "User-Agent": "air-quality/0.1"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Live AQI provider is unavailable") from exc
    if not isinstance(payload.get("list"), list) or not payload["list"]:
        raise HTTPException(
            status_code=502,
            detail="Live AQI provider returned no observations",
        )
    return payload["list"][0]


def _fetch_location_name(lat: float, lon: float) -> str | None:
    token = os.getenv("OPENWEATHER_API_KEY")
    if not token:
        return None
    request = Request(
        f"https://api.openweathermap.org/geo/1.0/reverse"
        f"?lat={lat}&lon={lon}&limit=1&appid={quote(token)}",
        headers={"Accept": "application/json", "User-Agent": "air-quality/0.1"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            locations = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    if not isinstance(locations, list) or not locations:
        return None
    location = locations[0]
    parts = [
        location.get("name"),
        location.get("state"),
        location.get("country"),
    ]
    return ", ".join(dict.fromkeys(part for part in parts if part))


def _fetch_geocoding(query: str) -> list[dict[str, Any]]:
    token = os.getenv("OPENWEATHER_API_KEY")
    if not token:
        raise HTTPException(status_code=503, detail="Live AQI is not configured")
    request = Request(
        f"https://api.openweathermap.org/geo/1.0/direct"
        f"?q={quote(query)}&limit=5&appid={quote(token)}",
        headers={"Accept": "application/json", "User-Agent": "air-quality/0.1"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Location search provider is unavailable") from exc
    if not isinstance(payload, list):
        raise HTTPException(status_code=502, detail="Location search returned an invalid response")
    return [
        {
            "name": ", ".join(dict.fromkeys(part for part in (
                item.get("name"), item.get("state"), item.get("country"),
            ) if part)),
            "latitude": item.get("lat"),
            "longitude": item.get("lon"),
        }
        for item in payload
    ]


def _fetch_pollution_forecast(lat: float, lon: float) -> list[dict[str, Any]]:
    token = os.getenv("OPENWEATHER_API_KEY")
    request = Request(
        f"https://api.openweathermap.org/data/2.5/air_pollution/forecast"
        f"?lat={lat}&lon={lon}&appid={quote(token or '')}",
        headers={"Accept": "application/json", "User-Agent": "air-quality/0.1"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Live pollution forecast is unavailable") from exc
    result = []
    for item in payload.get("list", [])[:48]:
        level = item.get("main", {}).get("aqi")
        result.append({
            "target_time": datetime.fromtimestamp(item["dt"]).astimezone().isoformat(),
            "prediction": {1: 25.0, 2: 75.0, 3: 150.0, 4: 250.0, 5: 400.0}.get(level),
        })
    return result


def _advisory(aqi: float | None, pollutants: dict[str, float | None] | None = None, forecast: list[dict[str, Any]] | None = None) -> str:
    pollutants = pollutants or {}
    forecast = forecast or []
    actions: list[str] = []
    if aqi is None:
        return "AQI unavailable. Check local official guidance before outdoor activity."
    if aqi <= 50:
        message = "Air is good. Normal outdoor activity is generally safe."
    if aqi <= 100:
        message = "Air is acceptable. Sensitive people should monitor symptoms."
    if aqi <= 200:
        message = "Sensitive people should reduce prolonged outdoor exertion and consider a mask."
    if aqi <= 300:
        message = "Avoid prolonged outdoor activity. Keep windows closed and use a well-fitted mask outside."
    if aqi <= 400:
        message = "Avoid outdoor activity where possible. Use air filtration indoors and wear a high-quality mask."
    if aqi > 400:
        message = "Stay indoors, close windows, use air purification, and follow local health authority guidance."
    if pollutants.get("pm2_5") and pollutants["pm2_5"] >= 60:
        actions.append("PM2.5 is high: wear an N95/KN95 mask outdoors.")
    if pollutants.get("pm10") and pollutants["pm10"] >= 100:
        actions.append("PM10 is high: avoid dust and heavy outdoor exercise.")
    if forecast and max((item.get("prediction") or 0) for item in forecast) > max(aqi, 0) + 50:
        actions.append("Forecast risk is increasing: plan outdoor activity for a cleaner period.")
    return f"{message} {' '.join(actions)}".strip()


def _live_anomalies(live: LiveAqiResponse, forecast: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    thresholds = {
        "pm2_5": ("PM2.5", 60),
        "pm10": ("PM10", 100),
        "no2": ("NO2", 200),
        "so2": ("SO2", 200),
        "o3": ("O3", 180),
        "co": ("CO", 10000),
    }
    findings = []
    if live.aqi is not None and live.aqi >= 200:
        findings.append({
            "metric": "AQI",
            "value": live.aqi,
            "reason": "AQI is in a poor-or-worse range",
        })
    for key, (label, threshold) in thresholds.items():
        value = live.pollutants.get(key)
        if value is not None and value >= threshold:
            findings.append({
                "metric": label,
                "value": value,
                "reason": f"{label} is above the live safety threshold",
            })
    forecast_values = [item.get("prediction") for item in (forecast or []) if item.get("prediction") is not None]
    if forecast_values and max(forecast_values) >= 200:
        findings.append({
            "metric": "Forecast AQI",
            "value": max(forecast_values),
            "reason": "A future forecast point reaches a poor-or-worse range",
        })
    return findings


def _save_live_reading(
    location: str,
    latitude: float,
    longitude: float,
    live: LiveAqiResponse,
) -> list[dict[str, Any]]:
    db = get_engine()
    with db.begin() as connection:
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS live_aqi_history ("
            "id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY, "
            "location_name VARCHAR(150) NULL, latitude DOUBLE NOT NULL, longitude DOUBLE NOT NULL, "
            "observed_at DATETIME NULL, fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "aqi DOUBLE NULL, aqi_bucket VARCHAR(32) NULL, pollutants_json JSON NOT NULL, "
            "source VARCHAR(50) NOT NULL, INDEX ix_live_history_location (latitude, longitude, fetched_at))"
        ))
        connection.execute(text(
            "INSERT INTO live_aqi_history "
            "(location_name, latitude, longitude, observed_at, aqi, aqi_bucket, pollutants_json, source) "
            "VALUES (:location, :latitude, :longitude, :observed_at, :aqi, :bucket, :pollutants, :source)"
        ), {
            "location": location,
            "latitude": latitude,
            "longitude": longitude,
            "observed_at": live.observed_at.replace(tzinfo=None) if live.observed_at else None,
            "aqi": live.aqi,
            "bucket": live.aqi_bucket,
            "pollutants": json.dumps(live.pollutants),
            "source": live.source,
        })
        rows = connection.execute(text(
            "SELECT fetched_at, observed_at, aqi, aqi_bucket, pollutants_json, source "
            "FROM live_aqi_history WHERE ABS(latitude - :latitude) < 0.01 "
            "AND ABS(longitude - :longitude) < 0.01 "
            "ORDER BY fetched_at DESC LIMIT 20"
        ), {"latitude": latitude, "longitude": longitude}).mappings().all()
    return [
        {
            "fetched_at": row["fetched_at"],
            "observed_at": row["observed_at"],
            "aqi": _numeric(row["aqi"]),
            "aqi_bucket": row["aqi_bucket"],
            "pollutants": json.loads(row["pollutants_json"]),
            "source": row["source"],
        }
        for row in rows
    ]


def _historical_trend(location: str) -> tuple[list[dict[str, Any]], str | None]:
    """Return the stored MySQL trend for a matching city or the full dataset."""
    db = get_engine()
    normalized_location = "".join(character.lower() for character in location if character.isalnum())
    with db.connect() as connection:
        cities = connection.execute(text(
            "SELECT DISTINCT city FROM air_quality_readings WHERE city IS NOT NULL"
        )).scalars().all()
        matching_city = next(
            (
                city for city in sorted(cities, key=len, reverse=True)
                if "".join(character.lower() for character in city if character.isalnum())
                in normalized_location
            ),
            None,
        )
        if matching_city:
            rows = connection.execute(text(
                "SELECT DATE(observed_at) AS point_date, AVG(aqi) AS value "
                "FROM air_quality_readings "
                "WHERE city = :city AND observed_at IS NOT NULL "
                "GROUP BY DATE(observed_at) ORDER BY point_date DESC LIMIT 30"
            ), {"city": matching_city}).mappings().all()
        else:
            rows = connection.execute(text(
                "SELECT DATE(observed_at) AS point_date, AVG(aqi) AS value "
                "FROM air_quality_readings "
                "WHERE observed_at IS NOT NULL "
                "GROUP BY DATE(observed_at) ORDER BY point_date DESC LIMIT 30"
            )).mappings().all()
    return [
        {"label": row["point_date"].isoformat(), "value": _numeric(row["value"])}
        for row in reversed(rows)
    ], matching_city


@app.get("/api/location-search", response_model=LocationSearchResponse)
def location_search(
    query: str = Query(min_length=2, max_length=100),
) -> LocationSearchResponse:
    return LocationSearchResponse(results=_fetch_geocoding(query))


@app.get("/api/location-report", response_model=LocationReportResponse)
def location_report(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    name: str | None = Query(default=None, max_length=150),
) -> LocationReportResponse:
    live = live_aqi(city=None, lat=lat, lon=lon)
    forecast = _fetch_pollution_forecast(lat, lon)
    location = name or live.city or "Selected location"
    history = _save_live_reading(location, lat, lon, live)
    historical_trend, historical_city = _historical_trend(location)
    return LocationReportResponse(
        location=location,
        latitude=lat,
        longitude=lon,
        live=live,
        forecast=forecast,
        advisory=_advisory(live.aqi, live.pollutants, forecast),
        anomalies=_live_anomalies(live, forecast),
        history=history,
        historical_trend=historical_trend,
        historical_city=historical_city,
    )


@app.get("/api/live-aqi", response_model=LiveAqiResponse)
def live_aqi(
    city: str | None = Query(default=None, min_length=1, max_length=100),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
) -> LiveAqiResponse:
    if city is None and (lat is None or lon is None):
        raise HTTPException(status_code=422, detail="Provide city or both lat and lon")
    if city is not None and (lat is not None or lon is not None):
        raise HTTPException(status_code=422, detail="Provide city or lat/lon, not both")
    if lat is None or lon is None:
        raise HTTPException(
            status_code=422,
            detail="OpenWeather live AQI requires latitude and longitude",
        )
    data = _fetch_openweather(lat, lon)
    components = data.get("components", {})
    level = data.get("main", {}).get("aqi")
    aqi = {1: 25.0, 2: 75.0, 3: 150.0, 4: 250.0, 5: 400.0}.get(level)
    pollutants = {
        "pm2_5": components.get("pm2_5"),
        "pm10": components.get("pm10"),
        "no2": components.get("no2"),
        "so2": components.get("so2"),
        "o3": components.get("o3"),
        "co": components.get("co"),
    }
    parsed_time = datetime.fromtimestamp(data["dt"]).astimezone() if data.get("dt") else None
    location_name = city or _fetch_location_name(lat, lon)
    return LiveAqiResponse(
        aqi=aqi,
        aqi_bucket=_aqi_bucket(aqi),
        city=location_name,
        observed_at=parsed_time,
        pollutants=pollutants,
        source="OpenWeather",
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db = get_engine()
    try:
        with db.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database health check failed") from exc
    return HealthResponse(status="ok", database="connected")


@app.get("/api/summary", response_model=SummaryResponse)
def summary(city: str | None = Query(default=None, min_length=1, max_length=100)) -> SummaryResponse:
    db = get_engine()
    filters = "WHERE city = :city" if city else ""
    params = {"city": city} if city else {}
    with db.connect() as connection:
        latest = connection.execute(text(
            f"SELECT aqi, aqi_bucket, observed_at, pm2_5, pm10, no_value, no2, "
            f"nox, nh3, so2, o3, co, benzene, toluene, xylene "
            f"FROM air_quality_readings {filters} AND observed_at = ("
            f"SELECT MAX(observed_at) FROM air_quality_readings {filters}) "
            "ORDER BY id DESC LIMIT 1"
        ) if city else text(
            "SELECT aqi, aqi_bucket, observed_at, pm2_5, pm10, no_value, no2, "
            "nox, nh3, so2, o3, co, benzene, toluene, xylene "
            "FROM air_quality_readings WHERE observed_at = "
            "(SELECT MAX(observed_at) FROM air_quality_readings) "
            "ORDER BY id DESC LIMIT 1"
        ), params).mappings().first()
        bounds = connection.execute(text(
            f"SELECT MIN(observed_at), MAX(observed_at) FROM air_quality_readings {filters}"
        ), params).one()
        trend = connection.execute(text(
            "SELECT DATE(observed_at) AS point_date, AVG(aqi) AS value "
            f"FROM air_quality_readings {'WHERE city = :city AND' if city else 'WHERE'} "
            "observed_at IS NOT NULL GROUP BY DATE(observed_at) "
            "ORDER BY point_date DESC LIMIT 30"
        ), params).mappings().all()
    if latest is None:
        raise HTTPException(status_code=404, detail="No observations found")
    trend_points = [
        {"label": row["point_date"].isoformat(), "value": _numeric(row["value"])}
        for row in reversed(trend)
    ]
    forecast = [
        {"label": item["target_time"], "value": item["prediction"]}
        for item in _artifact("forecasts.json", required=False)
        if item["target"] == "aqi" and (city is None or item["city"] == city)
    ][:48]
    return SummaryResponse(
        aqi=_numeric(latest["aqi"]),
        aqi_bucket=latest["aqi_bucket"],
        latest_observation=latest["observed_at"],
        data_range=f"{bounds[0].date().isoformat()} to {bounds[1].date().isoformat()}",
        pollutants={
            key: _numeric(latest[key])
            for key in (
                "pm2_5",
                "pm10",
                "no_value",
                "no2",
                "nox",
                "nh3",
                "co",
                "so2",
                "o3",
                "benzene",
                "toluene",
                "xylene",
            )
        },
        trend=trend_points,
        forecast=forecast,
    )


@app.get("/api/readings", response_model=PaginatedReadings)
def readings(
    city: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PaginatedReadings:
    db = get_engine()
    where = "WHERE city = :city" if city else ""
    params: dict[str, Any] = {"city": city, "limit": limit, "offset": offset}
    with db.connect() as connection:
        total = connection.execute(
            text(f"SELECT COUNT(*) FROM air_quality_readings {where}"), params
        ).scalar_one()
        rows = connection.execute(text(
            f"SELECT id, city, observed_at, aqi, aqi_bucket, pm2_5, pm10, "
            f"no2, so2, o3, station FROM air_quality_readings {where} "
            "ORDER BY observed_at DESC, id DESC LIMIT :limit OFFSET :offset"
        ), params).mappings().all()
    return PaginatedReadings(items=[dict(row) for row in rows], total=total, limit=limit, offset=offset)


@app.get("/api/analytics", response_model=AnalyticsResponse)
def analytics() -> AnalyticsResponse:
    db = get_engine()
    with db.connect() as connection:
        city_counts = connection.execute(text(
            "SELECT city, COUNT(*) AS rows_total, AVG(aqi) AS aqi_mean "
            "FROM air_quality_readings GROUP BY city ORDER BY city"
        )).mappings().all()
        yearly = connection.execute(text(
            "SELECT YEAR(observed_at) AS year, COUNT(*) AS rows_total, AVG(aqi) AS aqi_mean "
            "FROM air_quality_readings WHERE observed_at IS NOT NULL "
            "GROUP BY YEAR(observed_at) ORDER BY year"
        )).mappings().all()
        buckets = connection.execute(text(
            "SELECT COALESCE(aqi_bucket, '[missing]') AS aqi_bucket, COUNT(*) AS rows_total "
            "FROM air_quality_readings GROUP BY aqi_bucket ORDER BY rows_total DESC"
        )).mappings().all()
    return AnalyticsResponse(
        city_counts=[dict(row) for row in city_counts],
        yearly_aqi_summary=[dict(row) for row in yearly],
        aqi_bucket_counts=[dict(row) for row in buckets],
    )


@app.get("/api/forecasts", response_model=ForecastResponse)
def forecasts(city: str | None = Query(default=None, min_length=1, max_length=100)) -> ForecastResponse:
    items = _artifact("forecasts.json")
    if city:
        items = [item for item in items if item["city"] == city]
    return ForecastResponse(items=items, available=bool(items))


@app.get("/api/anomalies", response_model=AnomalyResponse)
def anomalies(city: str | None = Query(default=None, min_length=1, max_length=100)) -> AnomalyResponse:
    items = _artifact("anomalies.json")
    if city:
        items = [item for item in items if item["city"] == city]
    return AnomalyResponse(items=items, available=bool(items))

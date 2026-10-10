"""FastAPI application for verified historical air-quality data."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.engine import Engine

from air_quality.api.schemas import (
    AnalyticsResponse,
    AnomalyResponse,
    ForecastResponse,
    HealthResponse,
    PaginatedReadings,
    SummaryResponse,
)
from air_quality.db.connection import create_database_engine, load_environment


ROOT = Path(__file__).resolve().parents[3]
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
    description="Historical air-quality analytics API; forecast endpoints remain empty until models are trained.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
    ],
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
            f"SELECT aqi, aqi_bucket, observed_at, pm2_5, pm10, no2, so2, o3, co "
            f"FROM air_quality_readings {filters} AND observed_at = ("
            f"SELECT MAX(observed_at) FROM air_quality_readings {filters}) "
            "ORDER BY id DESC LIMIT 1"
        ) if city else text(
            "SELECT aqi, aqi_bucket, observed_at, pm2_5, pm10, no2, so2, o3, co "
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
    return SummaryResponse(
        aqi=_numeric(latest["aqi"]),
        aqi_bucket=latest["aqi_bucket"],
        latest_observation=latest["observed_at"],
        data_range=f"{bounds[0].date().isoformat()} to {bounds[1].date().isoformat()}",
        pollutants={
            key: _numeric(latest[key])
            for key in ("pm2_5", "pm10", "no2", "so2", "o3", "co")
        },
        trend=trend_points,
        forecast=[],
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
def forecasts() -> ForecastResponse:
    return ForecastResponse(items=[], available=False)


@app.get("/api/anomalies", response_model=AnomalyResponse)
def anomalies() -> AnomalyResponse:
    return AnomalyResponse(items=[], available=False)

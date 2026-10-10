"""Pydantic response models for the dashboard API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str


class SummaryResponse(BaseModel):
    aqi: float | None
    aqi_bucket: str | None
    latest_observation: datetime | None
    data_range: str | None
    pollutants: dict[str, float | None]
    trend: list[dict[str, Any]]
    forecast: list[dict[str, Any]]


class ReadingResponse(BaseModel):
    id: int
    city: str
    observed_at: datetime | None
    aqi: float | None
    aqi_bucket: str | None
    pm2_5: float | None
    pm10: float | None
    no2: float | None
    so2: float | None
    o3: float | None
    station: str | None


class PaginatedReadings(BaseModel):
    items: list[ReadingResponse]
    total: int
    limit: int
    offset: int


class AnalyticsResponse(BaseModel):
    city_counts: list[dict[str, Any]]
    yearly_aqi_summary: list[dict[str, Any]]
    aqi_bucket_counts: list[dict[str, Any]]


class ForecastResponse(BaseModel):
    items: list[dict[str, Any]]
    available: bool


class AnomalyResponse(BaseModel):
    items: list[dict[str, Any]]
    available: bool

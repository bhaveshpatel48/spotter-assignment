"""Open-Meteo hourly forecast client with bulk requests and caching (ADR-0003)."""

from collections.abc import Sequence
from datetime import UTC, datetime

import structlog
from django.core.cache import cache
from pydantic import BaseModel

from core.errors import ProviderError, ProviderQuotaExceeded
from core.events import EventName
from providers import http
from trip_planning.models import PointForecast

PROVIDER = "open_meteo"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARIABLES = "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall"
LOCATIONS_PER_REQUEST = 500
# Forecasts update about hourly; caching for an hour saves the free daily quota (10,000 calls).
CACHE_SECONDS = 60 * 60
# Bulk requests can take several seconds, longer than the default provider timeout.
TIMEOUT_SECONDS = 30.0
SECONDS_PER_HOUR = 3600

# Multipliers that convert the returned unit to mph or inches.
WIND_UNITS = {"mp/h": 1.0, "mph": 1.0, "km/h": 1 / 1.609344}
DEPTH_UNITS = {"inch": 1.0, "mm": 1 / 25.4, "cm": 1 / 2.54}

logger = structlog.get_logger(__name__)

type LatLon = tuple[float, float]


class _HourlyUnits(BaseModel):
    wind_speed_10m: str
    wind_gusts_10m: str
    rain: str
    showers: str
    snowfall: str


class _Hourly(BaseModel):
    time: list[int]
    wind_speed_10m: list[float | None]
    wind_gusts_10m: list[float | None]
    rain: list[float | None]
    showers: list[float | None]
    snowfall: list[float | None]


class _LocationForecast(BaseModel):
    hourly_units: _HourlyUnits
    hourly: _Hourly


def get_hourly_forecasts(
    points: Sequence[LatLon], start: datetime, end: datetime
) -> dict[LatLon, PointForecast]:
    """Hourly forecasts from `start` to `end` (both inclusive, UTC) for each (lat, lon) point."""
    keys = {point: _cache_key(point, start, end) for point in points}
    cached = cache.get_many(list(keys.values()))
    forecasts = {point: cached[key] for point, key in keys.items() if key in cached}
    missing = [point for point in points if point not in forecasts]
    logger.info(
        EventName.WEATHER_REQUESTED,
        location_count=len(points),
        cached=len(forecasts),
        fetched=len(missing),
        hours=round((end - start).total_seconds() / SECONDS_PER_HOUR) + 1,
    )

    for chunk_start in range(0, len(missing), LOCATIONS_PER_REQUEST):
        chunk = missing[chunk_start : chunk_start + LOCATIONS_PER_REQUEST]
        fetched = dict(zip(chunk, _fetch(chunk, start, end), strict=True))
        cache.set_many({keys[point]: f for point, f in fetched.items()}, CACHE_SECONDS)
        forecasts.update(fetched)
    return forecasts


def _fetch(points: Sequence[LatLon], start: datetime, end: datetime) -> list[PointForecast]:
    response = http.send(
        PROVIDER,
        "forecast",
        "POST",
        FORECAST_URL,
        timeout=TIMEOUT_SECONDS,
        data={
            "latitude": ",".join(str(lat) for lat, _ in points),
            "longitude": ",".join(str(lon) for _, lon in points),
            "hourly": HOURLY_VARIABLES,
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timeformat": "unixtime",
            "timezone": "GMT",
            "start_hour": _hour_param(start),
            "end_hour": _hour_param(end),
        },
    )
    if response.status_code == 429 and "daily" in response.text.lower():
        raise ProviderQuotaExceeded(
            "The weather service's free daily limit is used up. Please try again tomorrow."
        )
    http.raise_for_status(PROVIDER, "forecast", response)
    body = response.json()
    # A single location comes back as an object; several come back as a list in request order.
    locations = body if isinstance(body, list) else [body]
    if len(locations) != len(points):
        raise ProviderError("The weather service returned an unexpected number of locations.")
    return [_to_point_forecast(_LocationForecast.model_validate(item)) for item in locations]


def _to_point_forecast(item: _LocationForecast) -> PointForecast:
    units, hourly = item.hourly_units, item.hourly
    if not hourly.time:
        raise ProviderError("The weather service returned no forecast hours.")
    wind = _factor(WIND_UNITS, units.wind_speed_10m)
    gust = _factor(WIND_UNITS, units.wind_gusts_10m)
    rain = _factor(DEPTH_UNITS, units.rain)
    showers = _factor(DEPTH_UNITS, units.showers)
    snow = _factor(DEPTH_UNITS, units.snowfall)

    return PointForecast(
        start=datetime.fromtimestamp(hourly.time[0], UTC),
        wind_mph=_scaled(hourly.wind_speed_10m, wind),
        gust_mph=_scaled(hourly.wind_gusts_10m, gust),
        # Large-scale rain and convective showers together are the rain rate (ADR-0007).
        rain_in_hr=tuple(
            r + s
            for r, s in zip(
                _scaled(hourly.rain, rain), _scaled(hourly.showers, showers), strict=True
            )
        ),
        snow_in_hr=_scaled(hourly.snowfall, snow),
    )


def _factor(table: dict[str, float], unit: str) -> float:
    if unit not in table:
        raise ProviderError(f"The weather service returned an unknown unit: {unit}.")
    return table[unit]


def _scaled(values: list[float | None], factor: float) -> tuple[float, ...]:
    # Missing hours are treated as calm and dry.
    return tuple((value or 0.0) * factor for value in values)


def _hour_param(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:00")


def _cache_key(point: LatLon, start: datetime, end: datetime) -> str:
    return f"weather:{point[0]}:{point[1]}:{start:%Y%m%d%H}:{end:%Y%m%d%H}"

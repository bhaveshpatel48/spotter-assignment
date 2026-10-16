"""Matching forecast hours to ETAs (ADR-0006)."""

from datetime import datetime, timedelta

from trip_planning.models import PointForecast, WeatherSample

HOUR = timedelta(hours=1)


def floor_hour(moment: datetime) -> datetime:
    return moment.replace(minute=0, second=0, microsecond=0)


def ceil_hour(moment: datetime) -> datetime:
    floored = floor_hour(moment)
    return floored if floored == moment else floored + HOUR


def round_hour(moment: datetime) -> datetime:
    floored = floor_hour(moment)
    return floored + HOUR if moment - floored >= HOUR / 2 else floored


def weather_at(forecast: PointForecast, eta: datetime) -> WeatherSample:
    """Rain, snow and gusts are totals/maxima for the preceding hour, so they use the hour
    that contains the ETA. Wind is an instant value, so it uses the nearest hour."""
    period = _index(forecast, ceil_hour(eta))
    instant = _index(forecast, round_hour(eta))
    return WeatherSample(
        wind_mph=forecast.wind_mph[instant],
        gust_mph=forecast.gust_mph[period],
        rain_in_hr=forecast.rain_in_hr[period],
        snow_in_hr=forecast.snow_in_hr[period],
    )


def _index(forecast: PointForecast, hour: datetime) -> int:
    index = int((hour - forecast.start) / HOUR)
    return min(max(index, 0), len(forecast.wind_mph) - 1)

from datetime import UTC, datetime, timedelta

import pytest
from django.core.cache import cache

from trip_planning.models import Coordinate, PointForecast, Route, RouteProgress


@pytest.fixture(autouse=True)
def _isolated_settings(settings):
    settings.TOMTOM_API_KEY = "test-key"
    cache.clear()


def straight_route(
    start: Coordinate, end: Coordinate, points: int = 101, hours: float = 10.0
) -> Route:
    """A straight route with evenly spaced points, travelled at constant speed."""
    coords = tuple(
        Coordinate(
            lat=start.lat + (end.lat - start.lat) * i / (points - 1),
            lon=start.lon + (end.lon - start.lon) * i / (points - 1),
        )
        for i in range(points)
    )
    from trip_planning.geo import METERS_PER_MILE, cumulative_miles

    return Route(
        points=coords,
        length_m=cumulative_miles(coords)[-1] * METERS_PER_MILE,
        travel_time_s=hours * 3600,
        progress=(RouteProgress(point_index=points - 1, travel_time_s=hours * 3600),),
    )


def calm_forecast(start: datetime, hours: int = 400, **overrides) -> PointForecast:
    values = {"wind_mph": 5.0, "gust_mph": 10.0, "rain_in_hr": 0.0, "snow_in_hr": 0.0}
    values.update(overrides)
    return PointForecast(start=start, **{k: (v,) * hours for k, v in values.items()})


NOW = datetime(2026, 10, 16, 12, 30, tzinfo=UTC)
DEPARTURE = NOW + timedelta(hours=2)

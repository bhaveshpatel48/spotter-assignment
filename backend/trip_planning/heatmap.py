"""Weather locations along the routes and the 48-hour heatmap values (ADR-0009).

One set of locations serves both checkpoints and the heatmap: every checkpoint plus a sample
every few miles along every route, rounded to a grid so nearby points share one forecast.
The heatmap therefore follows each road instead of covering a wide area around it.
"""

from collections.abc import Callable, Sequence

from trip_planning.geo import resample, snap
from trip_planning.models import Coordinate, HeatmapPoint, PointForecast, Route
from trip_planning.risk import risk_level

# About 7 miles. The grid only gets coarser if a very long trip would exceed the budget.
SNAP_STEP_DEG = 0.1
# Closer together than one grid cell, so no stretch of road is skipped.
ROUTE_SAMPLE_MILES = 5.0
HEATMAP_HOURS = 48


def weather_locations(
    routes: Sequence[Route], checkpoints: Sequence[Coordinate], max_locations: int
) -> tuple[float, list[Coordinate]]:
    """The grid step (degrees) and the locations to fetch weather for, within the budget."""
    points = [
        *checkpoints,
        *(point for route in routes for point in resample(route.points, ROUTE_SAMPLE_MILES)),
    ]
    step = SNAP_STEP_DEG
    while True:
        keys = {snap(point, step) for point in points}
        if len(keys) <= max_locations:
            return step, [Coordinate(lat=lat, lon=lon) for lat, lon in sorted(keys)]
        step = round(step + SNAP_STEP_DEG, 4)


def build_heatmap(
    locations: Sequence[Coordinate],
    forecast_for: Callable[[Coordinate], PointForecast],
    load_weight_lb: int,
) -> list[HeatmapPoint]:
    """Risk level for each location and each of the first 48 forecast hours."""
    points = []
    for coordinate in locations:
        forecast = forecast_for(coordinate)
        hours = min(HEATMAP_HOURS, len(forecast.wind_mph))
        risk = tuple(
            int(
                risk_level(
                    forecast.wind_mph[h],
                    forecast.rain_in_hr[h],
                    forecast.snow_in_hr[h],
                    load_weight_lb,
                )
            )
            for h in range(hours)
        )
        points.append(HeatmapPoint(coordinate=coordinate, risk=risk))
    return points

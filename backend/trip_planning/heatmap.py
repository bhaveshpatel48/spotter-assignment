"""The heatmap grid along the trip corridor and its 48-hour risk values (ADR-0009)."""

from collections.abc import Callable, Sequence

from trip_planning.geo import resample
from trip_planning.models import Coordinate, HeatmapPoint, PointForecast, Route
from trip_planning.risk import risk_level

GRID_START_STEP_DEG = 0.2
GRID_STEP_INCREMENT_DEG = 0.1
# Route samples must be closer together than one grid step, so no cell along the route is missed.
SAMPLE_STEP_MILES = 5.0
HEATMAP_HOURS = 48


def weather_grid(routes: Sequence[Route], max_points: int) -> tuple[float, list[Coordinate]]:
    """The finest grid (step in degrees, points) whose corridor around all routes fits the budget.

    The corridor covers each route cell and its 8 neighbours, so it is about three cells wide.
    """
    samples = [p for route in routes for p in resample(route.points, SAMPLE_STEP_MILES)]
    step = GRID_START_STEP_DEG
    while True:
        cells = set()
        for point in samples:
            row, col = round(point.lat / step), round(point.lon / step)
            cells.update((row + dr, col + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1))
        if len(cells) <= max_points:
            points = [
                Coordinate(lat=round(row * step, 4), lon=round(col * step, 4))
                for row, col in sorted(cells)
            ]
            return step, points
        step = round(step + GRID_STEP_INCREMENT_DEG, 4)


def build_heatmap(
    grid: Sequence[Coordinate],
    forecast_for: Callable[[Coordinate], PointForecast | None],
    load_weight_lb: int,
) -> list[HeatmapPoint]:
    """Risk level for each grid point and each of the first 48 forecast hours."""
    points = []
    for coordinate in grid:
        forecast = forecast_for(coordinate)
        if forecast is None:
            continue
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

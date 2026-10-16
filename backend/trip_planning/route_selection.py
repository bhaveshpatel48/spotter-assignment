"""Choosing up to three meaningfully different routes (ADR-0005)."""

import math
from collections.abc import Sequence

from trip_planning.geo import METERS_PER_MILE, cumulative_miles, resample
from trip_planning.models import BoundingBox, Route

MAX_ROUTES = 3
# An alternative must have at least this share of its road away from the routes already chosen.
MIN_DISTINCT_SHARE = 0.10
# Routes closer than about one grid cell (~1 km) count as the same road.
CELL_DEG = 0.01
SAMPLE_STEP_MILES = 0.5
AVOID_BOX_HALF_SIZE_KM = 15.0
KM_PER_DEG_LAT = 111.0

type Cell = tuple[int, int]


def select_distinct_routes(main: Route, candidates: Sequence[Route]) -> list[Route]:
    """The main route plus the candidates that differ most from every route already chosen."""
    chosen = [main]
    chosen_cells = [_cells(main)]
    remaining = [(route, resample(route.points, SAMPLE_STEP_MILES)) for route in candidates]

    while len(chosen) < MAX_ROUTES and remaining:
        scores = [
            min(_distinct_share(samples, cells) for cells in chosen_cells)
            for _, samples in remaining
        ]
        best = max(range(len(remaining)), key=scores.__getitem__)
        if scores[best] < MIN_DISTINCT_SHARE:
            break
        route, _ = remaining.pop(best)
        chosen.append(route)
        chosen_cells.append(_cells(route))
    return chosen


def avoid_box_around_midpoint(route: Route) -> BoundingBox:
    """A square around the middle of the route, used to force the provider onto another road."""
    miles = cumulative_miles(route.points)
    middle = next(i for i, m in enumerate(miles) if m >= miles[-1] / 2)
    center = route.points[middle]
    half_lat = AVOID_BOX_HALF_SIZE_KM / KM_PER_DEG_LAT
    half_lon = AVOID_BOX_HALF_SIZE_KM / (KM_PER_DEG_LAT * math.cos(math.radians(center.lat)))
    return BoundingBox(
        south=center.lat - half_lat,
        west=center.lon - half_lon,
        north=center.lat + half_lat,
        east=center.lon + half_lon,
    )


def route_miles(route: Route) -> float:
    return route.length_m / METERS_PER_MILE


def _cells(route: Route) -> set[Cell]:
    return {_cell(p.lat, p.lon) for p in resample(route.points, SAMPLE_STEP_MILES)}


def _cell(lat: float, lon: float) -> Cell:
    return round(lat / CELL_DEG), round(lon / CELL_DEG)


def _distinct_share(samples, cells: set[Cell]) -> float:
    """Share of sample points with no point of the other route in their 3x3 cell neighbourhood."""
    if not samples:
        return 0.0
    away = 0
    for point in samples:
        row, col = _cell(point.lat, point.lon)
        if not any((row + dr, col + dc) in cells for dr in (-1, 0, 1) for dc in (-1, 0, 1)):
            away += 1
    return away / len(samples)

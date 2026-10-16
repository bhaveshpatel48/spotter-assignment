import math
from collections.abc import Sequence

from trip_planning.models import Coordinate

METERS_PER_MILE = 1609.344
EARTH_RADIUS_MILES = 3958.8

# Contiguous United States (lower 48), as a simple bounding box.
CONTIGUOUS_US_SOUTH = 24.3
CONTIGUOUS_US_NORTH = 49.5
CONTIGUOUS_US_WEST = -125.0
CONTIGUOUS_US_EAST = -66.8


def is_in_contiguous_us(lat: float, lon: float) -> bool:
    return (
        CONTIGUOUS_US_SOUTH <= lat <= CONTIGUOUS_US_NORTH
        and CONTIGUOUS_US_WEST <= lon <= CONTIGUOUS_US_EAST
    )


def haversine_miles(a: Coordinate, b: Coordinate) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def cumulative_miles(points: Sequence[Coordinate]) -> list[float]:
    """Distance in miles from the first point to each point along the polyline."""
    totals = [0.0]
    for previous, current in zip(points, points[1:], strict=False):
        totals.append(totals[-1] + haversine_miles(previous, current))
    return totals


def interpolate(a: Coordinate, b: Coordinate, fraction: float) -> Coordinate:
    return Coordinate(
        lat=a.lat + (b.lat - a.lat) * fraction, lon=a.lon + (b.lon - a.lon) * fraction
    )


def resample(points: Sequence[Coordinate], step_miles: float) -> list[Coordinate]:
    """Points every `step_miles` along the polyline, always including both ends."""
    if len(points) < 2:
        return list(points)
    cumulative = cumulative_miles(points)
    samples = [points[0]]
    target = step_miles
    segment = 0
    while target < cumulative[-1]:
        while cumulative[segment + 1] < target:
            segment += 1
        length = cumulative[segment + 1] - cumulative[segment]
        fraction = (target - cumulative[segment]) / length if length else 0.0
        samples.append(interpolate(points[segment], points[segment + 1], fraction))
        target += step_miles
    samples.append(points[-1])
    return samples


def snap(coordinate: Coordinate, step_deg: float) -> tuple[float, float]:
    """Round a coordinate to a grid of `step_deg` degrees, so nearby points share one key."""
    return (
        round(round(coordinate.lat / step_deg) * step_deg, 4),
        round(round(coordinate.lon / step_deg) * step_deg, 4),
    )

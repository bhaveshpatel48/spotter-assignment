"""Checkpoint placement and ETAs (ADR-0006)."""

from bisect import bisect_right
from datetime import datetime, timedelta

from trip_planning.geo import METERS_PER_MILE, cumulative_miles, interpolate
from trip_planning.models import CheckpointPosition, Route
from trip_planning.rest_breaks import rest_seconds_before


def place_checkpoints(
    route: Route,
    departure: datetime,
    spacing_miles: int,
    include_rest_breaks: bool = False,
) -> list[CheckpointPosition]:
    """A checkpoint at the origin, every `spacing_miles` along the route, and at the destination."""
    points = route.points
    miles = _scaled_cumulative_miles(route)
    drive_s = _driving_seconds_per_point(route, miles)
    total = miles[-1]

    marks = [float(m) for m in range(0, int(total), spacing_miles) if m < total]
    marks.append(total)

    positions = []
    for mark in marks:
        segment = min(bisect_right(miles, mark) - 1, len(points) - 2)
        length = miles[segment + 1] - miles[segment]
        fraction = (mark - miles[segment]) / length if length else 0.0
        driving = drive_s[segment] + fraction * (drive_s[segment + 1] - drive_s[segment])
        elapsed = driving + (rest_seconds_before(driving) if include_rest_breaks else 0.0)
        positions.append(
            CheckpointPosition(
                mile=round(mark, 1),
                coordinate=interpolate(points[segment], points[segment + 1], fraction),
                eta=departure + timedelta(seconds=round(elapsed)),
            )
        )
    return positions


def _scaled_cumulative_miles(route: Route) -> list[float]:
    """Polyline distance, scaled so the total matches the provider's route length."""
    miles = cumulative_miles(route.points)
    route_miles = route.length_m / METERS_PER_MILE
    if miles[-1] == 0:
        return miles
    scale = route_miles / miles[-1]
    return [m * scale for m in miles]


def _driving_seconds_per_point(route: Route, miles: list[float]) -> list[float]:
    """Travel time at every point, interpolated by distance between the provider's anchors."""
    last = len(route.points) - 1
    anchors = {0: 0.0, last: route.travel_time_s}
    for entry in route.progress:
        if 0 < entry.point_index < last:
            anchors[entry.point_index] = entry.travel_time_s
    indexes = sorted(anchors)

    seconds = [0.0] * len(route.points)
    for start, end in zip(indexes, indexes[1:], strict=False):
        span = miles[end] - miles[start]
        for i in range(start, end + 1):
            fraction = (miles[i] - miles[start]) / span if span else 0.0
            seconds[i] = anchors[start] + fraction * (anchors[end] - anchors[start])
    return seconds

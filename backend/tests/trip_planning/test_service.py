from datetime import timedelta

import pytest

from core.errors import NoRouteFound, TripOutsideForecastRange
from tests.conftest import DEPARTURE, NOW, calm_forecast, straight_route
from trip_planning.enums import CheckpointSpacing, RiskLevel
from trip_planning.geo import snap
from trip_planning.models import Coordinate, Place, TripRequest
from trip_planning.service import plan_trip
from trip_planning.weather import floor_hour

ORIGIN = Place(label="A", lat=35.0, lon=-97.0)
DESTINATION = Place(label="B", lat=37.0, lon=-97.0)
MIDDLE = 36.0


def detour(offset_lon: float, hours: float = 10.0):
    middle = Coordinate(lat=MIDDLE, lon=-97.0 + offset_lon)
    first = straight_route(ORIGIN.coordinate, middle, 51, hours / 2)
    second = straight_route(middle, DESTINATION.coordinate, 51, hours / 2)
    return first.model_copy(
        update={
            "points": first.points + second.points[1:],
            "length_m": first.length_m + second.length_m,
            "travel_time_s": first.travel_time_s + second.travel_time_s,
            "progress": (),
        }
    )


def trip(**overrides) -> TripRequest:
    values = {
        "origin": ORIGIN,
        "destination": DESTINATION,
        "departure_time": DEPARTURE,
        "load_weight_lb": 35_000,
        "checkpoint_spacing": CheckpointSpacing.TWENTY_FIVE,
    }
    values.update(overrides)
    return TripRequest(**values)


class FakeRoutes:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, origin, destination, *, depart_at, load_kg, max_alternatives, avoid=None):
        self.calls.append({"load_kg": load_kg, "avoid": avoid})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def windy_east_of(lon: float):
    """Calm forecasts, except High wind east of `lon` in the middle third of the trip."""

    def fetch(points, start, end):
        return {
            p: calm_forecast(start, wind_mph=40.0 if p[1] > lon and 35.5 <= p[0] <= 36.5 else 5.0)
            for p in points
        }

    return fetch


def test_recommends_the_route_avoiding_bad_weather():
    straight, west, east = detour(0.0), detour(-0.6), detour(0.6)
    fetch_routes = FakeRoutes([straight, west, east])
    plan = plan_trip(
        trip(), fetch_routes=fetch_routes, fetch_forecasts=windy_east_of(-97.05), now=NOW
    )

    assert [r.rank for r in plan.routes] == [1, 2, 3]
    assert plan.recommended_route_id == "route-2"  # only the western detour avoids the wind
    recommended, *others = plan.routes
    assert recommended.summary.miles_by_risk[RiskLevel.HIGH] == 0
    assert all(r.summary.miles_by_risk[RiskLevel.HIGH] > 0 for r in others)
    assert fetch_routes.calls[0]["load_kg"] == round(35_000 * 0.45359237)
    assert plan.warnings == ()


def test_heatmap_starts_at_departure_hour_with_48_values():
    plan = plan_trip(
        trip(),
        fetch_routes=FakeRoutes([detour(0.0), detour(-0.6), detour(0.6)]),
        fetch_forecasts=windy_east_of(-97.05),
        now=NOW,
    )
    assert plan.heatmap.start_time == floor_hour(DEPARTURE)
    assert plan.heatmap.cell_size_deg == 0.1  # a short trip fits the finest grid
    assert plan.heatmap.points
    assert all(len(p.risk) == 48 for p in plan.heatmap.points)


def test_fallback_request_avoids_midpoint_when_too_few_routes():
    fetch_routes = FakeRoutes([detour(0.0)], [detour(-0.6), detour(0.6)])
    plan = plan_trip(trip(), fetch_routes=fetch_routes, fetch_forecasts=windy_east_of(0), now=NOW)
    assert len(plan.routes) == 3
    assert fetch_routes.calls[1]["avoid"] is not None


def test_warns_when_fewer_than_three_routes_exist():
    plan = plan_trip(
        trip(),
        fetch_routes=FakeRoutes([detour(0.0)], NoRouteFound()),
        fetch_forecasts=windy_east_of(0),
        now=NOW,
    )
    assert len(plan.routes) == 1
    assert [w.code for w in plan.warnings] == ["FEWER_ROUTES"]


def test_warns_when_every_route_has_no_travel_miles():
    def storm(points, start, end):
        return {p: calm_forecast(start, wind_mph=60.0) for p in points}

    plan = plan_trip(
        trip(),
        fetch_routes=FakeRoutes([detour(0.0), detour(-0.6), detour(0.6)]),
        fetch_forecasts=storm,
        now=NOW,
    )
    assert "NO_SAFE_ROUTE" in [w.code for w in plan.warnings]


def test_rejects_trips_ending_beyond_the_forecast():
    with pytest.raises(TripOutsideForecastRange):
        plan_trip(
            trip(departure_time=NOW + timedelta(days=15, hours=20)),
            fetch_routes=FakeRoutes([detour(0.0, hours=10), detour(-0.6), detour(0.6)]),
            fetch_forecasts=windy_east_of(0),
            now=NOW,
        )


def test_weather_is_requested_once_for_the_whole_trip():
    calls = []

    def fetch(points, start, end):
        calls.append((len(points), start, end))
        return windy_east_of(0)(points, start, end)

    plan_trip(
        trip(),
        fetch_routes=FakeRoutes([detour(0.0), detour(-0.6), detour(0.6)]),
        fetch_forecasts=fetch,
        now=NOW,
    )
    [(count, start, end)] = calls
    assert count <= 550
    assert start == floor_hour(DEPARTURE)
    assert end - start >= timedelta(hours=47)


def test_every_checkpoint_gets_weather_at_its_own_location():
    requested = set()

    def fetch(points, start, end):
        requested.update(points)
        return windy_east_of(0)(points, start, end)

    plan = plan_trip(
        trip(checkpoint_spacing=CheckpointSpacing.TEN),
        fetch_routes=FakeRoutes([detour(0.0), detour(-0.6), detour(0.6)]),
        fetch_forecasts=fetch,
        now=NOW,
    )
    for route in plan.routes:
        for checkpoint in route.checkpoints:
            assert snap(checkpoint.coordinate, 0.1) in requested


def test_slider_covers_a_departure_days_away():
    departure = NOW + timedelta(days=3, hours=4, minutes=20)
    plan = plan_trip(
        trip(departure_time=departure),
        fetch_routes=FakeRoutes([detour(0.0), detour(-0.6), detour(0.6)]),
        fetch_forecasts=windy_east_of(0),
        now=NOW,
    )
    start = plan.heatmap.start_time
    assert start == floor_hour(departure)
    arrival = plan.routes[0].summary.arrival_time
    assert start <= arrival <= start + timedelta(hours=48)

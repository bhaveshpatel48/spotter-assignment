from datetime import timedelta

import pytest

from tests.conftest import DEPARTURE, straight_route
from trip_planning.checkpoints import place_checkpoints
from trip_planning.models import Coordinate, Route, RouteProgress
from trip_planning.rest_breaks import rest_seconds_before

# About 69 miles per degree of latitude, so this route is roughly 138 miles long.
START, END = Coordinate(lat=35.0, lon=-97.0), Coordinate(lat=37.0, lon=-97.0)


def test_checkpoints_at_origin_every_spacing_and_destination():
    route = straight_route(START, END)
    positions = place_checkpoints(route, DEPARTURE, 25)
    miles = [p.mile for p in positions]
    assert miles[:6] == [0, 25, 50, 75, 100, 125]
    assert miles[-1] == pytest.approx(route.length_m / 1609.344, abs=0.1)
    assert positions[0].coordinate == START
    assert positions[-1].coordinate.lat == pytest.approx(END.lat)


def test_eta_follows_constant_speed_between_anchors():
    route = straight_route(START, END, hours=10)
    positions = place_checkpoints(route, DEPARTURE, 50)
    total = positions[-1].mile
    for p in positions:
        expected = DEPARTURE + timedelta(hours=10 * p.mile / total)
        assert abs((p.eta - expected).total_seconds()) <= 60


def test_eta_uses_provider_progress_anchors():
    base = straight_route(START, END, points=3, hours=10)
    # The first half takes 8 hours (slow), the second half 2 hours.
    route = Route(
        points=base.points,
        length_m=base.length_m,
        travel_time_s=base.travel_time_s,
        progress=(RouteProgress(point_index=1, travel_time_s=8 * 3600),),
    )
    positions = place_checkpoints(route, DEPARTURE, 10)
    middle = min(positions, key=lambda p: abs(p.mile - positions[-1].mile / 2))
    assert abs((middle.eta - DEPARTURE).total_seconds() - 8 * 3600) < 15 * 60


def test_rest_breaks_shift_later_etas():
    route = straight_route(START, END, hours=20)
    without = place_checkpoints(route, DEPARTURE, 10)
    with_breaks = place_checkpoints(route, DEPARTURE, 10, include_rest_breaks=True)
    assert with_breaks[-1].eta - without[-1].eta == timedelta(hours=11)  # 30 min x2 + 10 h
    assert with_breaks[1].eta == without[1].eta


@pytest.mark.parametrize(
    ("driving_hours", "rest_hours"),
    [
        (0, 0),
        (8, 0),  # break is due after 8 hours, not at 8 hours
        (8.5, 0.5),
        (11, 0.5),  # rest is due after 11 hours
        (12, 10.5),
        (19.5, 11.0),  # 10.5 + second shift's 30-minute break
        (22, 11.0),
        (23, 21.0),  # two full shifts of rest, 1 hour into the third shift
    ],
)
def test_rest_seconds_before(driving_hours, rest_hours):
    assert rest_seconds_before(driving_hours * 3600) == rest_hours * 3600

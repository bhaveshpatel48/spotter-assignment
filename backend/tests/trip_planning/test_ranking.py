from datetime import UTC, datetime

from trip_planning.enums import RiskLevel
from trip_planning.models import (
    Checkpoint,
    Coordinate,
    RiskAssessment,
    RouteSummary,
    WeatherSample,
)
from trip_planning.ranking import average_risk, has_no_safe_route, miles_by_risk, rank_order

T = datetime(2026, 10, 16, tzinfo=UTC)
CALM = WeatherSample(wind_mph=0, gust_mph=0, rain_in_hr=0, snow_in_hr=0)


def checkpoint(mile: float, level: RiskLevel) -> Checkpoint:
    return Checkpoint(
        index=0,
        mile=mile,
        coordinate=Coordinate(lat=0, lon=0),
        eta=T,
        weather=CALM,
        risk=RiskAssessment(level=level),
    )


def summary(no_travel=0.0, severe=0.0, high=0.0, avg=0.0, travel_s=3600) -> RouteSummary:
    miles = dict.fromkeys(RiskLevel, 0.0)
    miles.update({RiskLevel.NO_TRAVEL: no_travel, RiskLevel.SEVERE: severe, RiskLevel.HIGH: high})
    return RouteSummary(
        distance_miles=100,
        travel_time_s=travel_s,
        departure_time=T,
        arrival_time=T,
        miles_by_risk=miles,
        average_risk=avg,
    )


def test_each_checkpoint_covers_the_road_to_the_next_one():
    checkpoints = [
        checkpoint(0, RiskLevel.LOW),
        checkpoint(25, RiskLevel.HIGH),
        checkpoint(50, RiskLevel.LOW),
        checkpoint(60, RiskLevel.SEVERE),  # destination: covers no road
    ]
    miles = miles_by_risk(checkpoints)
    assert miles[RiskLevel.LOW] == 35
    assert miles[RiskLevel.HIGH] == 25
    assert miles[RiskLevel.SEVERE] == 0


def test_average_risk_is_mile_weighted():
    miles = dict.fromkeys(RiskLevel, 0.0)
    miles.update({RiskLevel.LOW: 75, RiskLevel.SEVERE: 25})
    assert average_risk(miles) == 0.75  # (0*75 + 3*25) / 100


def test_average_risk_of_zero_miles_is_zero():
    assert average_risk(dict.fromkeys(RiskLevel, 0.0)) == 0.0


def test_ranking_order_of_preference():
    routes = [
        summary(severe=10),  # 0
        summary(no_travel=1),  # 1: any No Travel ranks last
        summary(high=50),  # 2: fewer Severe miles beats fewer High miles
        summary(high=50, avg=0.3),  # 3: same High miles, higher average
        summary(high=50, avg=0.3, travel_s=1800),  # 4: same average, faster
    ]
    assert rank_order(routes) == [2, 4, 3, 0, 1]


def test_ties_keep_provider_order():
    assert rank_order([summary(), summary()]) == [0, 1]


def test_no_safe_route_only_when_every_route_has_no_travel_miles():
    assert has_no_safe_route([summary(no_travel=1), summary(no_travel=5)])
    assert not has_no_safe_route([summary(no_travel=1), summary()])

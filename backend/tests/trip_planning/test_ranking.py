from datetime import UTC, datetime

from trip_planning.enums import RiskLevel
from trip_planning.models import (
    Checkpoint,
    Coordinate,
    RiskAssessment,
    RouteSummary,
    WeatherSample,
)
from trip_planning.ranking import (
    average_risk,
    has_no_safe_route,
    miles_by_risk,
    rank_order,
    ranking_reasons,
)

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


def test_reason_when_only_travel_time_differs():
    # The real Denver -> Salt Lake City case: all Low risk, the fastest route wins.
    fast, slow, slowest = (
        summary(travel_s=27_240),
        summary(travel_s=32_220),
        summary(travel_s=39_000),
    )
    assert ranking_reasons([slow, fast, slowest]) == [
        "Same weather risk as Route 1, but 1 h 23 m slower.",
        "Same weather risk as Route 2, and 1 h 23 m faster.",
        "Same weather risk as Route 2, but 1 h 53 m slower.",
    ]


def test_reason_names_the_first_rule_that_differs():
    safe, severe = summary(high=40), summary(severe=25)
    assert ranking_reasons([severe, safe]) == [
        "More Severe miles than Route 1 (25 vs 0 mi).",
        "Fewer Severe miles than Route 2 (0 vs 25 mi).",
    ]


def test_reason_for_no_travel_high_and_average_risk():
    no_travel = summary(no_travel=10)
    high = summary(high=30)
    lower_avg, higher_avg = summary(avg=0.1), summary(avg=0.4)
    assert (
        ranking_reasons([no_travel, high])[0] == "More No Travel miles than Route 1 (10 vs 0 mi)."
    )
    assert ranking_reasons([high, lower_avg])[0] == "More High miles than Route 1 (30 vs 0 mi)."
    assert ranking_reasons([lower_avg, higher_avg]) == [
        "Lower average risk than Route 2 (0.10 vs 0.40).",
        "Higher average risk than Route 1 (0.40 vs 0.10).",
    ]


def test_reason_for_identical_and_single_routes():
    assert ranking_reasons([summary(), summary()])[0] == (
        "Same weather risk and travel time as Route 2."
    )
    assert ranking_reasons([summary()]) == ["The only practical route for this trip."]

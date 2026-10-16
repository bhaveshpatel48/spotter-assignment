from tests.conftest import straight_route
from trip_planning.models import Coordinate
from trip_planning.route_selection import avoid_box_around_midpoint, select_distinct_routes

A = Coordinate(lat=35.0, lon=-97.0)
B = Coordinate(lat=37.0, lon=-97.0)


def detour(offset_lon: float):
    """A route from A to B that bulges sideways through a point offset in longitude."""
    middle = Coordinate(lat=36.0, lon=-97.0 + offset_lon)
    first, second = straight_route(A, middle, 51), straight_route(middle, B, 51)
    return first.model_copy(
        update={
            "points": first.points + second.points[1:],
            "length_m": first.length_m + second.length_m,
        }
    )


def test_keeps_main_plus_most_distinct_alternatives():
    main = straight_route(A, B)
    near_duplicate = straight_route(A, B, points=73)
    west, east = detour(-0.5), detour(0.5)
    chosen = select_distinct_routes(main, [near_duplicate, west, east])
    assert chosen == [main, west, east]


def test_alternatives_must_also_differ_from_each_other():
    main = straight_route(A, B)
    west, west_again = detour(-0.5), detour(-0.5)
    assert select_distinct_routes(main, [west, west_again]) == [main, west]


def test_avoid_box_is_centered_on_route_midpoint():
    box = avoid_box_around_midpoint(straight_route(A, B))
    assert box.south < 36.0 < box.north
    assert box.west < -97.0 < box.east
    assert round(box.north - box.south, 2) == 0.27  # 30 km tall

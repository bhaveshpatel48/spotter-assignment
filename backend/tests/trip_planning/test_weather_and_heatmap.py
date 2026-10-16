from datetime import UTC, datetime, timedelta

from tests.conftest import straight_route
from trip_planning.geo import snap
from trip_planning.heatmap import build_heatmap, weather_grid
from trip_planning.models import Coordinate, PointForecast
from trip_planning.weather import weather_at

START = datetime(2026, 10, 16, 0, tzinfo=UTC)


def hourly(values):
    return tuple(float(v) for v in values)


FORECAST = PointForecast(
    start=START,
    wind_mph=hourly(range(10)),  # wind at hour h is h mph
    gust_mph=hourly(range(100, 110)),
    rain_in_hr=hourly(v / 100 for v in range(10)),
    snow_in_hr=hourly([0] * 10),
)


def test_rain_uses_hour_containing_eta_and_wind_uses_nearest_hour():
    sample = weather_at(FORECAST, START + timedelta(hours=3, minutes=40))
    assert sample.rain_in_hr == 0.04  # value at 04:00 covers 03:00-04:00
    assert sample.gust_mph == 104
    assert sample.wind_mph == 4  # 03:40 rounds to 04:00

    sample = weather_at(FORECAST, START + timedelta(hours=3, minutes=10))
    assert sample.wind_mph == 3
    assert sample.rain_in_hr == 0.04


def test_eta_outside_forecast_is_clamped():
    assert weather_at(FORECAST, START - timedelta(hours=5)).wind_mph == 0
    assert weather_at(FORECAST, START + timedelta(days=5)).wind_mph == 9


def test_weather_grid_gets_coarser_to_fit_budget():
    routes = [straight_route(Coordinate(lat=33, lon=-97), Coordinate(lat=42, lon=-88))]
    fine_step, fine = weather_grid(routes, max_points=1000)
    coarse_step, coarse = weather_grid(routes, max_points=150)
    assert fine_step == 0.2
    assert len(coarse) <= 150 < len(fine)
    assert coarse_step > fine_step


def test_every_point_on_the_route_falls_in_a_grid_cell():
    route = straight_route(Coordinate(lat=33, lon=-97), Coordinate(lat=42, lon=-88), points=2000)
    step, grid = weather_grid([route], max_points=300)
    cells = {(c.lat, c.lon) for c in grid}
    assert all(snap(p, step) in cells for p in route.points)


def test_heatmap_has_48_hourly_risk_values_with_load_rules():
    forecast = PointForecast(
        start=START,
        wind_mph=hourly([38] * 60),
        gust_mph=hourly([40] * 60),
        rain_in_hr=hourly([0] * 60),
        snow_in_hr=hourly([0] * 60),
    )
    point = Coordinate(lat=35, lon=-97)
    [light] = build_heatmap([point], lambda _: forecast, load_weight_lb=20_000)
    [heavy] = build_heatmap([point], lambda _: forecast, load_weight_lb=45_000)
    assert len(light.risk) == 48
    assert set(light.risk) == {2}  # High
    assert set(heavy.risk) == {3}  # Severe


def test_heatmap_skips_points_without_forecast():
    assert build_heatmap([Coordinate(lat=35, lon=-97)], lambda _: None, 20_000) == []

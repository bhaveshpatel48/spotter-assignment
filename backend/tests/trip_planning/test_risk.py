import pytest

from trip_planning.enums import RiskLevel
from trip_planning.models import WeatherSample
from trip_planning.risk import assess, load_level, rain_level, risk_level, snow_level, wind_level

L, M, H, S, N = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
)


@pytest.mark.parametrize(
    ("mph", "expected"),
    [
        (0, L),
        (24.9, L),
        (25, M),
        (34.9, M),
        (35, H),
        (44.9, H),
        (45, S),
        (54.9, S),
        (55, N),
        (80, N),
    ],
)
def test_wind_bands(mph, expected):
    assert wind_level(mph) == expected


@pytest.mark.parametrize(
    ("rate", "expected"),
    [
        (0, L),
        (0.09, L),
        (0.10, M),
        (0.24, M),
        (0.25, H),
        (0.49, H),
        (0.50, S),
        (1.00, S),
        (1.01, N),
    ],
)
def test_rain_bands_boundary_goes_to_higher_band_except_no_travel(rate, expected):
    assert rain_level(rate) == expected


@pytest.mark.parametrize(
    ("rate", "expected"),
    [(0, L), (0.49, L), (0.5, M), (0.99, M), (1.0, H), (1.99, H), (2.0, S), (3.0, S), (3.01, N)],
)
def test_snow_bands(rate, expected):
    assert snow_level(rate) == expected


@pytest.mark.parametrize(
    ("mph", "load", "expected"),
    [
        (55, 1_000, N),  # >= 55 mph: No Travel for any load
        (45, 30_000, L),  # 45-54 mph needs > 30,000 lb
        (45, 30_001, N),
        (54.9, 30_001, N),
        (35, 40_000, L),  # 35-44 mph needs > 40,000 lb
        (35, 40_001, S),
        (44.9, 40_001, S),
        (34.9, 80_000, L),
    ],
)
def test_load_rules(mph, load, expected):
    assert load_level(mph, load) == expected


def test_combined_level_is_worst_condition_raised_by_load():
    assert risk_level(10, 0.3, 0.6, 20_000) == H  # rain High beats snow Moderate
    assert risk_level(38, 0.0, 0.0, 20_000) == H  # wind alone
    assert risk_level(38, 0.0, 0.0, 42_000) == S  # load raises High wind to Severe
    assert risk_level(10, 1.5, 0.0, 42_000) == N  # load rules never lower a level


def test_assess_explains_each_contributing_condition():
    weather = WeatherSample(wind_mph=38, gust_mph=50, rain_in_hr=0.12, snow_in_hr=0)
    result = assess(weather, 42_000)
    assert result.level == S
    assert result.reasons == (
        "Wind 38 mph (High)",
        "Rain 0.12 in/hr (Moderate)",
        "Load 42,000 lb with wind 38 mph (Severe)",
    )


def test_assess_calm_weather_has_no_reasons():
    weather = WeatherSample(wind_mph=5, gust_mph=8, rain_in_hr=0, snow_in_hr=0)
    assert assess(weather, 80_000).reasons == ()

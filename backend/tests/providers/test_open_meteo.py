import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from core.errors import ProviderError, ProviderQuotaExceeded
from providers import http, open_meteo

FIXTURE = json.loads(
    (Path(__file__).parent.parent / "fixtures/open_meteo_two_locations.json").read_text()
)
# A real Open-Meteo response for Denver, CO and Salt Lake City, UT.
DENVER, SALT_LAKE_CITY = (39.7, -105.0), (40.8, -111.9)
POINTS = [DENVER, SALT_LAKE_CITY]
START = datetime.fromtimestamp(FIXTURE[0]["hourly"]["time"][0], UTC)
END = datetime.fromtimestamp(FIXTURE[0]["hourly"]["time"][-1], UTC)


@pytest.fixture
def mock_http(monkeypatch):
    def install(handler):
        requests = []

        def record(request):
            requests.append(request)
            return handler(request)

        monkeypatch.setattr(http, "_client", httpx.Client(transport=httpx.MockTransport(record)))
        return requests

    return install


def test_parses_bulk_response_in_request_order(mock_http):
    requests = mock_http(lambda _: httpx.Response(200, json=FIXTURE))
    forecasts = open_meteo.get_hourly_forecasts(POINTS, START, END)

    denver = forecasts[DENVER]
    assert denver.start == START
    assert denver.wind_mph == tuple(FIXTURE[0]["hourly"]["wind_speed_10m"])
    assert forecasts[SALT_LAKE_CITY].gust_mph == tuple(FIXTURE[1]["hourly"]["wind_gusts_10m"])
    body = requests[0].content.decode()
    assert "latitude=39.7%2C40.8" in body
    assert f"start_hour={START:%Y-%m-%dT%H}%3A00" in body
    assert f"end_hour={END:%Y-%m-%dT%H}%3A00" in body


def test_rain_rate_is_rain_plus_showers_and_metric_units_are_converted(mock_http):
    item = json.loads(json.dumps(FIXTURE[0]))
    item["hourly_units"].update({"rain": "mm", "showers": "mm", "snowfall": "cm"})
    item["hourly"].update(
        {"rain": [25.4, 0, 0, 0], "showers": [12.7, 0, None, 0], "snowfall": [2.54, 0, 0, 0]}
    )
    mock_http(lambda _: httpx.Response(200, json=item))
    [forecast] = open_meteo.get_hourly_forecasts([DENVER], START, END).values()
    assert forecast.rain_in_hr[0] == pytest.approx(1.5)
    assert forecast.snow_in_hr[0] == pytest.approx(1.0)
    assert forecast.rain_in_hr[2] == 0.0


def test_cached_points_are_not_requested_again(mock_http):
    requests = mock_http(lambda _: httpx.Response(200, json=FIXTURE))
    open_meteo.get_hourly_forecasts(POINTS, START, END)
    open_meteo.get_hourly_forecasts(POINTS, START, END)
    assert len(requests) == 1


def test_rate_limit_maps_to_quota_error(mock_http):
    mock_http(lambda _: httpx.Response(429, json={"error": True}))
    with pytest.raises(ProviderQuotaExceeded, match="try again in a minute"):
        open_meteo.get_hourly_forecasts(POINTS, START, END)


def test_daily_limit_says_try_tomorrow(mock_http):
    body = {"reason": "Daily API request limit exceeded. Please try again tomorrow.", "error": True}
    mock_http(lambda _: httpx.Response(429, json=body))
    with pytest.raises(ProviderQuotaExceeded, match="tomorrow"):
        open_meteo.get_hourly_forecasts(POINTS, START, END)


def test_server_error_is_retried_once(mock_http):
    responses = iter([httpx.Response(503), httpx.Response(200, json=FIXTURE)])
    requests = mock_http(lambda _: next(responses))
    assert len(open_meteo.get_hourly_forecasts(POINTS, START, END)) == 2
    assert len(requests) == 2


def test_unexpected_location_count_is_an_error(mock_http):
    mock_http(lambda _: httpx.Response(200, json=FIXTURE[:1]))
    with pytest.raises(ProviderError):
        open_meteo.get_hourly_forecasts(POINTS, START, END)

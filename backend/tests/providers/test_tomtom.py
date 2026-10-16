import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from core.errors import (
    NoRouteFound,
    ProviderError,
    ProviderNotConfigured,
    ProviderQuotaExceeded,
    ProviderTimeout,
)
from providers import http, tomtom
from trip_planning.models import BoundingBox, Coordinate

# Denver, CO to Salt Lake City, UT.
ORIGIN = Coordinate(lat=39.7392, lon=-104.9903)
DESTINATION = Coordinate(lat=40.7608, lon=-111.8910)

# A real TomTom truck-route response for Denver to Salt Lake City (main route + 2 alternatives),
# thinned to every 50th point to keep the file small.
ROUTE_RESPONSE = json.loads(
    (Path(__file__).parent.parent / "fixtures/tomtom_denver_salt_lake_city.json").read_text()
)

SEARCH_RESPONSE = {
    "results": [
        {"address": {"freeformAddress": "Denver, CO"}, "position": {"lat": 39.74, "lon": -104.99}},
        {
            "address": {"freeformAddress": "Denver Street, Anchorage, AK"},
            "position": {"lat": 61.2, "lon": -149.9},
        },
    ]
}


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


def calculate(**overrides):
    kwargs = {
        "depart_at": datetime.now(UTC) + timedelta(hours=3),
        "load_kg": 18_000,
        "max_alternatives": 5,
    }
    kwargs.update(overrides)
    return tomtom.calculate_routes(ORIGIN, DESTINATION, **kwargs)


def test_parses_routes_and_sends_truck_parameters(mock_http):
    requests = mock_http(lambda _: httpx.Response(200, json=ROUTE_RESPONSE))
    routes = calculate()

    assert len(routes) == 3
    main = routes[0]
    assert len(main.points) == 145
    assert main.length_m == 860_706
    assert main.travel_time_s == 27_243
    assert main.progress[0].point_index == 0
    assert main.progress[-1].point_index == len(main.points) - 1
    assert main.progress[-1].travel_time_s == 27_243

    params = requests[0].url.params
    assert requests[0].method == "GET"
    assert params["travelMode"] == "truck"
    assert params["vehicleWeight"] == "18000"
    assert params["vehicleCommercial"] == "true"
    assert params.get_list("extendedRouteRepresentation") == ["distance", "travelTime"]


def test_avoid_area_is_sent_as_post_body(mock_http):
    requests = mock_http(lambda _: httpx.Response(200, json=ROUTE_RESPONSE))
    calculate(avoid=BoundingBox(south=41, west=-108, north=41.3, east=-107.6))
    assert requests[0].method == "POST"
    assert b'"avoidAreas"' in requests[0].content


def test_departure_now_is_sent_as_now(mock_http):
    requests = mock_http(lambda _: httpx.Response(200, json=ROUTE_RESPONSE))
    calculate(depart_at=datetime.now(UTC))
    assert requests[0].url.params["departAt"] == "now"


@pytest.mark.parametrize("code", ["NO_ROUTE_FOUND", "MAP_MATCHING_FAILURE"])
def test_no_route_found(mock_http, code):
    # Real format, e.g. a destination in the Gulf of Mexico gives MAP_MATCHING_FAILURE.
    body = {"formatVersion": "0.0.12", "detailedError": {"code": code, "message": "Engine error"}}
    mock_http(lambda _: httpx.Response(400, json=body))
    with pytest.raises(NoRouteFound):
        calculate()


def test_other_bad_requests_are_provider_errors(mock_http):
    body = {"detailedError": {"code": "INVALID_REQUEST", "message": "Bad parameter"}}
    mock_http(lambda _: httpx.Response(400, json=body))
    with pytest.raises(ProviderError):
        calculate()


def test_invalid_key_is_reported_as_not_configured(mock_http):
    body = {"detailedError": {"code": "Unauthorized", "message": "Missing credentials"}}
    mock_http(lambda _: httpx.Response(401, json=body))
    with pytest.raises(ProviderNotConfigured, match="invalid"):
        calculate()


def test_forbidden_maps_to_quota_error(mock_http):
    mock_http(lambda _: httpx.Response(403, text="Developer Over Qps"))
    with pytest.raises(ProviderQuotaExceeded):
        calculate()


def test_timeout_maps_to_timeout_error(mock_http):
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    mock_http(handler)
    with pytest.raises(ProviderTimeout):
        calculate()


def test_missing_api_key(settings):
    settings.TOMTOM_API_KEY = ""
    with pytest.raises(ProviderNotConfigured):
        calculate()


def test_geocode_keeps_contiguous_us_results_and_caches(mock_http):
    requests = mock_http(lambda _: httpx.Response(200, json=SEARCH_RESPONSE))
    places = tomtom.geocode("Denver")
    assert [p.label for p in places] == ["Denver, CO"]
    assert tomtom.geocode("  DENVER ") == places
    assert len(requests) == 1
    assert requests[0].url.params["countrySet"] == "US"

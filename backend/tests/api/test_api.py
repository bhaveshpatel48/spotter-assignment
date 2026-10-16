import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.errors import ProviderQuotaExceeded
from tests.conftest import calm_forecast
from tests.trip_planning.test_service import FakeRoutes, detour
from trip_planning.models import Place


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def fake_providers(monkeypatch):
    def forecasts(points, start, end):
        return {p: calm_forecast(start) for p in points}

    monkeypatch.setattr(
        "api.views.tomtom.calculate_routes", FakeRoutes([detour(0.0), detour(-0.6), detour(0.6)])
    )
    monkeypatch.setattr("api.views.open_meteo.get_hourly_forecasts", forecasts)


def plan_body(**overrides):
    body = {
        "origin": {"label": "A", "lat": 35.0, "lon": -97.0},
        "destination": {"label": "B", "lat": 37.0, "lon": -97.0},
        "departure_time": (timezone.now() + timedelta(hours=2)).isoformat(),
        "load_weight_lb": 35000,
        "checkpoint_spacing_miles": 25,
    }
    body.update(overrides)
    return body


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_is_generated_or_reused(client):
    generated = client.get("/api/health")["X-Request-ID"]
    assert uuid.UUID(generated)

    incoming = str(uuid.uuid4())
    assert client.get("/api/health", HTTP_X_REQUEST_ID=incoming)["X-Request-ID"] == incoming
    assert client.get("/api/health", HTTP_X_REQUEST_ID="not-a-uuid")["X-Request-ID"] != "not-a-uuid"


def test_plan_returns_ranked_routes_checkpoints_and_heatmap(client, fake_providers):
    response = client.post("/api/plan", plan_body(), format="json")
    assert response.status_code == 200
    data = response.json()

    assert data["recommended_route_id"] == data["routes"][0]["id"]
    route = data["routes"][0]
    assert set(route["summary"]["miles_by_risk"]) == {
        "LOW",
        "MODERATE",
        "HIGH",
        "SEVERE",
        "NO_TRAVEL",
    }
    assert route["geometry"][0] == [-97.0, 35.0]  # GeoJSON order: [lon, lat]
    checkpoint = route["checkpoints"][0]
    assert checkpoint["risk_level"] == "LOW"
    assert checkpoint["eta"].endswith("Z")
    assert set(checkpoint["weather"]) == {"wind_mph", "gust_mph", "rain_in_hr", "snow_in_hr"}
    assert data["heatmap"]["hours"] == 48
    assert data["heatmap"]["cell_size_deg"] >= 0.1
    assert len(data["heatmap"]["points"][0]["risk"]) == 48


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"load_weight_lb": 0}, "load_weight_lb"),
        ({"load_weight_lb": 80001}, "load_weight_lb"),
        ({"checkpoint_spacing_miles": 15}, "checkpoint_spacing_miles"),
        ({"departure_time": "2020-01-01T00:00:00Z"}, "departure_time"),
        ({"origin": {"label": "Anchorage", "lat": 61.2, "lon": -149.9}}, "origin"),
        ({"destination": {"label": "A", "lat": 35.0, "lon": -97.0}}, "non_field_errors"),
    ],
)
def test_plan_validation_errors(client, overrides, field):
    response = client.post("/api/plan", plan_body(**overrides), format="json")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in error["fields"]
    assert error["request_id"] == response["X-Request-ID"]


def test_provider_errors_use_the_error_format(client, monkeypatch):
    def quota_exceeded(*args, **kwargs):
        raise ProviderQuotaExceeded()

    monkeypatch.setattr("api.views.tomtom.calculate_routes", quota_exceeded)
    response = client.post("/api/plan", plan_body(), format="json")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PROVIDER_QUOTA_EXCEEDED"


def test_geocode(client, monkeypatch):
    monkeypatch.setattr(
        "api.views.tomtom.geocode", lambda q: [Place(label="Denver, CO", lat=39.74, lon=-104.99)]
    )
    response = client.get("/api/geocode", {"q": "den"})
    assert response.status_code == 200
    assert response.json() == {"results": [{"label": "Denver, CO", "lat": 39.74, "lon": -104.99}]}


def test_geocode_requires_three_characters(client):
    response = client.get("/api/geocode", {"q": "de"})
    assert response.status_code == 400
    assert "q" in response.json()["error"]["fields"]

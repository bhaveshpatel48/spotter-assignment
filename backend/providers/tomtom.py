"""TomTom Search (geocoding) and Routing clients (ADR-0002)."""

import hashlib
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import structlog
from django.conf import settings
from django.core.cache import cache
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from core.errors import NoRouteFound, ProviderNotConfigured
from core.events import EventName
from providers import http
from trip_planning.geo import is_in_contiguous_us
from trip_planning.models import BoundingBox, Coordinate, Place, Route, RouteProgress

PROVIDER = "tomtom"
BASE_URL = "https://api.tomtom.com"
GEOCODE_CACHE_SECONDS = 24 * 3600
GEOCODE_LIMIT = 5
# Geographies, point addresses, address ranges and streets; no points of interest.
GEOCODE_INDEXES = "Geo,PAD,Addr,Str,XStr"
# Routing error codes that mean "no drivable route", as opposed to a service failure.
NO_ROUTE_CODES = {"NO_ROUTE_FOUND", "MAP_MATCHING_FAILURE"}

logger = structlog.get_logger(__name__)


# --- TomTom response models -------------------------------------------------


class _TomTomModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class _Position(_TomTomModel):
    lat: float
    lon: float


class _Address(_TomTomModel):
    freeform_address: str


class _SearchResult(_TomTomModel):
    address: _Address
    position: _Position


class _SearchResponse(_TomTomModel):
    results: list[_SearchResult] = []


class _LatLon(_TomTomModel):
    latitude: float
    longitude: float


class _Leg(_TomTomModel):
    points: list[_LatLon]


class _Summary(_TomTomModel):
    length_in_meters: float
    travel_time_in_seconds: float


class _Progress(_TomTomModel):
    point_index: int
    travel_time_in_seconds: float | None = None


class _Route(_TomTomModel):
    summary: _Summary
    legs: list[_Leg]
    progress: list[_Progress] = []


class _RouteResponse(_TomTomModel):
    routes: list[_Route] = []


class _DetailedError(_TomTomModel):
    code: str = ""
    message: str = ""


class _ErrorResponse(_TomTomModel):
    detailed_error: _DetailedError = _DetailedError()


# --- Public functions ---------------------------------------------------------


def geocode(query: str) -> list[Place]:
    """Places in the contiguous US matching `query`. Results are cached for a day."""
    normalized = " ".join(query.lower().split())
    key = "geocode:" + hashlib.sha256(normalized.encode()).hexdigest()
    cached = cache.get(key)
    logger.info(
        EventName.GEOCODE_REQUESTED, query_length=len(normalized), cache_hit=cached is not None
    )
    if cached is not None:
        return cached

    response = http.send(
        PROVIDER,
        "search",
        "GET",
        f"{BASE_URL}/search/2/search/{quote(normalized, safe='')}.json",
        params={
            "key": _api_key(),
            "countrySet": "US",
            "limit": GEOCODE_LIMIT,
            "typeahead": "true",
            "idxSet": GEOCODE_INDEXES,
        },
    )
    _raise_for_status("search", response)
    results = _SearchResponse.model_validate(response.json()).results
    places = [
        Place(label=r.address.freeform_address, lat=r.position.lat, lon=r.position.lon)
        for r in results
        if is_in_contiguous_us(r.position.lat, r.position.lon)
    ]
    cache.set(key, places, GEOCODE_CACHE_SECONDS)
    return places


def calculate_routes(
    origin: Coordinate,
    destination: Coordinate,
    *,
    depart_at: datetime,
    load_kg: int,
    max_alternatives: int,
    avoid: BoundingBox | None = None,
) -> list[Route]:
    """Truck routes from TomTom: the main route first, then alternatives."""
    locations = f"{origin.lat},{origin.lon}:{destination.lat},{destination.lon}"
    params = [
        ("key", _api_key()),
        ("travelMode", "truck"),
        ("vehicleCommercial", "true"),
        ("vehicleWeight", str(load_kg)),
        ("maxAlternatives", str(max_alternatives)),
        ("departAt", _depart_at_param(depart_at)),
        ("traffic", "true"),
        ("routeRepresentation", "polyline"),
        ("extendedRouteRepresentation", "distance"),
        ("extendedRouteRepresentation", "travelTime"),
    ]
    url = f"{BASE_URL}/routing/1/calculateRoute/{locations}/json"
    if avoid is None:
        response = http.send(PROVIDER, "calculateRoute", "GET", url, params=params)
    else:
        response = http.send(
            PROVIDER, "calculateRoute", "POST", url, params=params, json=_avoid_body(avoid)
        )

    if response.status_code == 400 and _error_code(response) in NO_ROUTE_CODES:
        raise NoRouteFound()
    _raise_for_status("calculateRoute", response)

    routes = [_to_route(r) for r in _RouteResponse.model_validate(response.json()).routes]
    if not routes:
        raise NoRouteFound()
    return routes


# --- Helpers ------------------------------------------------------------------


def _raise_for_status(endpoint: str, response) -> None:
    if response.status_code == 401:
        raise ProviderNotConfigured("The TomTom API key is invalid.")
    http.raise_for_status(PROVIDER, endpoint, response)


def _error_code(response) -> str:
    try:
        return _ErrorResponse.model_validate(response.json()).detailed_error.code
    except ValueError:
        return ""


def _api_key() -> str:
    if not settings.TOMTOM_API_KEY:
        raise ProviderNotConfigured("The TomTom API key is not configured.")
    return settings.TOMTOM_API_KEY


def _depart_at_param(depart_at: datetime) -> str:
    """TomTom rejects departure times in the past, so anything that is effectively now is 'now'."""
    if depart_at <= datetime.now(UTC) + timedelta(minutes=1):
        return "now"
    return depart_at.astimezone(UTC).replace(microsecond=0).isoformat()


def _avoid_body(box: BoundingBox) -> dict:
    return {
        "avoidAreas": {
            "rectangles": [
                {
                    "southWestCorner": {"latitude": box.south, "longitude": box.west},
                    "northEastCorner": {"latitude": box.north, "longitude": box.east},
                }
            ]
        }
    }


def _to_route(route: _Route) -> Route:
    points = tuple(
        Coordinate(lat=p.latitude, lon=p.longitude) for leg in route.legs for p in leg.points
    )
    progress = tuple(
        RouteProgress(point_index=p.point_index, travel_time_s=p.travel_time_in_seconds)
        for p in route.progress
        if p.travel_time_in_seconds is not None
    )
    return Route(
        points=points,
        length_m=route.summary.length_in_meters,
        travel_time_s=route.summary.travel_time_in_seconds,
        progress=progress,
    )

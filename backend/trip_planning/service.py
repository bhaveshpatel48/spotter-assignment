"""plan_trip(): routes → checkpoints → weather → risk → ranking → heatmap.

Provider functions are passed in, so this module never touches the network or Django.
"""

import math
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta

import structlog

from core.errors import NoRouteFound, TripOutsideForecastRange
from core.events import EventName
from trip_planning import ranking
from trip_planning.checkpoints import place_checkpoints
from trip_planning.enums import RiskLevel
from trip_planning.geo import snap
from trip_planning.heatmap import HEATMAP_HOURS, build_heatmap, weather_locations
from trip_planning.models import (
    BoundingBox,
    Checkpoint,
    CheckpointPosition,
    Coordinate,
    Heatmap,
    PlannedRoute,
    PlanWarning,
    PointForecast,
    Route,
    RouteSummary,
    TripPlan,
    TripRequest,
)
from trip_planning.risk import assess
from trip_planning.route_selection import (
    MAX_ROUTES,
    avoid_box_around_midpoint,
    route_miles,
    select_distinct_routes,
)
from trip_planning.weather import HOUR, floor_hour, weather_at

LB_TO_KG = 0.45359237
ALTERNATIVES_REQUESTED = 5
MIN_MILES_FOR_FALLBACK = 50
FORECAST_HORIZON = timedelta(days=16)
# Open-Meteo allows 600 calls/minute and each location counts as at least one call.
MAX_WEATHER_LOCATIONS = 550

logger = structlog.get_logger(__name__)

type LatLon = tuple[float, float]
# Signatures of providers.tomtom.calculate_routes and providers.open_meteo.get_hourly_forecasts.
type RouteFetcher = Callable[..., list[Route]]
type ForecastFetcher = Callable[[Sequence[LatLon], datetime, datetime], dict[LatLon, PointForecast]]


def plan_trip(
    request: TripRequest,
    *,
    fetch_routes: RouteFetcher,
    fetch_forecasts: ForecastFetcher,
    now: datetime,
) -> TripPlan:
    routes = _get_routes(request, fetch_routes)
    positions = [
        place_checkpoints(
            route,
            request.departure_time,
            request.checkpoint_spacing,
            request.include_rest_breaks,
        )
        for route in routes
    ]

    # The forecast window, and the heatmap's hour 0, start at the departure hour, so the
    # 0-48 h slider covers the trip itself even when departure is days away.
    window_start = floor_hour(request.departure_time)
    latest_eta = max(route_positions[-1].eta for route_positions in positions)
    if latest_eta > now + FORECAST_HORIZON - HOUR:
        raise TripOutsideForecastRange()
    hours = _forecast_hours(window_start, latest_eta)

    # One bulk request for every checkpoint and the road between them.
    checkpoint_coordinates = [
        p.coordinate for route_positions in positions for p in route_positions
    ]
    step, locations = weather_locations(routes, checkpoint_coordinates, MAX_WEATHER_LOCATIONS)
    forecasts = fetch_forecasts(
        [(c.lat, c.lon) for c in locations], window_start, window_start + (hours - 1) * HOUR
    )

    def forecast_at(coordinate: Coordinate) -> PointForecast:
        return forecasts[snap(coordinate, step)]

    summaries, checkpoints = [], []
    for route, route_positions in zip(routes, positions, strict=True):
        route_checkpoints = _assess_checkpoints(
            route_positions, forecast_at, request.load_weight_lb
        )
        checkpoints.append(route_checkpoints)
        summaries.append(_summarize(route, route_checkpoints, request.departure_time))

    order = ranking.rank_order(summaries)
    planned = tuple(
        PlannedRoute(
            id=f"route-{index + 1}",
            rank=rank,
            is_recommended=rank == 1,
            summary=summaries[index],
            geometry=routes[index].points,
            checkpoints=tuple(checkpoints[index]),
        )
        for rank, index in enumerate(order, start=1)
    )

    return TripPlan(
        generated_at=now,
        recommended_route_id=planned[0].id,
        warnings=tuple(_warnings(summaries)),
        routes=planned,
        heatmap=Heatmap(
            start_time=window_start,
            hours=HEATMAP_HOURS,
            cell_size_deg=step,
            points=tuple(build_heatmap(locations, forecast_at, request.load_weight_lb)),
        ),
    )


def _get_routes(request: TripRequest, fetch_routes: RouteFetcher) -> list[Route]:
    """Up to three distinct routes, with one avoid-area retry when fewer come back (ADR-0005)."""
    origin = request.origin.coordinate
    destination = request.destination.coordinate
    load_kg = round(request.load_weight_lb * LB_TO_KG)

    def fetch(avoid: BoundingBox | None = None) -> list[Route]:
        return fetch_routes(
            origin,
            destination,
            depart_at=request.departure_time,
            load_kg=load_kg,
            max_alternatives=ALTERNATIVES_REQUESTED,
            avoid=avoid,
        )

    main, *alternatives = fetch()
    selected = select_distinct_routes(main, alternatives)
    if len(selected) < MAX_ROUTES and route_miles(main) >= MIN_MILES_FOR_FALLBACK:
        try:
            extra = fetch(avoid_box_around_midpoint(main))
        except NoRouteFound:
            extra = []
        before = len(selected)
        selected = select_distinct_routes(main, [*selected[1:], *extra])
        logger.info(
            EventName.ROUTES_FALLBACK_USED, routes_before=before, routes_after=len(selected)
        )
    return selected


def _forecast_hours(window_start: datetime, latest_eta: datetime) -> int:
    """Hours of forecast needed, rounded up to whole days so cached forecasts are reused."""
    needed = max(HEATMAP_HOURS, math.ceil((latest_eta - window_start) / HOUR) + 2)
    return math.ceil(needed / 24) * 24


def _assess_checkpoints(
    positions: Sequence[CheckpointPosition], forecast_for, load_weight_lb: int
) -> list[Checkpoint]:
    checkpoints = []
    for index, position in enumerate(positions):
        forecast = forecast_for(position.coordinate)
        weather = weather_at(forecast, position.eta)
        checkpoints.append(
            Checkpoint(
                index=index,
                mile=position.mile,
                coordinate=position.coordinate,
                eta=position.eta,
                weather=weather,
                risk=assess(weather, load_weight_lb),
            )
        )
    return checkpoints


def _summarize(
    route: Route, checkpoints: Sequence[Checkpoint], departure: datetime
) -> RouteSummary:
    miles = ranking.miles_by_risk(checkpoints)
    arrival = checkpoints[-1].eta
    return RouteSummary(
        distance_miles=round(route_miles(route), 1),
        travel_time_s=round((arrival - departure).total_seconds()),
        departure_time=departure,
        arrival_time=arrival,
        miles_by_risk=miles,
        average_risk=ranking.average_risk(miles),
    )


def _warnings(summaries: Sequence[RouteSummary]) -> list[PlanWarning]:
    warnings = []
    if len(summaries) < MAX_ROUTES:
        warnings.append(
            PlanWarning(
                code="FEWER_ROUTES",
                message=f"Only {len(summaries)} practical route(s) exist for this trip.",
            )
        )
    if ranking.has_no_safe_route(summaries):
        logger.warning(EventName.PLAN_NO_SAFE_ROUTE, route_count=len(summaries))
        warnings.append(
            PlanWarning(
                code="NO_SAFE_ROUTE",
                message=(
                    f"Every route has {RiskLevel.NO_TRAVEL.label} conditions. "
                    "Consider delaying departure."
                ),
            )
        )
    return warnings

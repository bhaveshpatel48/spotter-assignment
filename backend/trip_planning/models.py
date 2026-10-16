"""Internal data passed between the trip-planning functions (see ADR-0011)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from trip_planning.enums import CheckpointSpacing, RiskLevel


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class Coordinate(FrozenModel):
    lat: float
    lon: float


class Place(FrozenModel):
    label: str
    lat: float
    lon: float

    @property
    def coordinate(self) -> Coordinate:
        return Coordinate(lat=self.lat, lon=self.lon)


class BoundingBox(FrozenModel):
    south: float
    west: float
    north: float
    east: float


class RouteProgress(FrozenModel):
    """Cumulative travel time at a route point, as reported by the routing provider."""

    point_index: int
    travel_time_s: float


class Route(FrozenModel):
    points: tuple[Coordinate, ...]
    length_m: float
    travel_time_s: float
    progress: tuple[RouteProgress, ...] = ()


class PointForecast(FrozenModel):
    """Hourly forecast for one location. Index i is the hour `start + i hours`."""

    start: datetime
    wind_mph: tuple[float, ...]
    gust_mph: tuple[float, ...]
    rain_in_hr: tuple[float, ...]
    snow_in_hr: tuple[float, ...]


class WeatherSample(FrozenModel):
    wind_mph: float
    gust_mph: float
    rain_in_hr: float
    snow_in_hr: float


class RiskAssessment(FrozenModel):
    level: RiskLevel
    reasons: tuple[str, ...] = ()


class CheckpointPosition(FrozenModel):
    mile: float
    coordinate: Coordinate
    eta: datetime


class Checkpoint(FrozenModel):
    index: int
    mile: float
    coordinate: Coordinate
    eta: datetime
    weather: WeatherSample
    risk: RiskAssessment


class RouteSummary(FrozenModel):
    distance_miles: float
    travel_time_s: int
    departure_time: datetime
    arrival_time: datetime
    miles_by_risk: dict[RiskLevel, float]
    average_risk: float


class PlannedRoute(FrozenModel):
    id: str
    rank: int
    is_recommended: bool
    summary: RouteSummary
    geometry: tuple[Coordinate, ...]
    checkpoints: tuple[Checkpoint, ...]


class HeatmapPoint(FrozenModel):
    coordinate: Coordinate
    risk: tuple[int, ...]


class Heatmap(FrozenModel):
    start_time: datetime
    hours: int
    # Spacing between neighbouring grid points, so the map can size each point to blend.
    cell_size_deg: float
    points: tuple[HeatmapPoint, ...]


class PlanWarning(FrozenModel):
    code: str
    message: str


class TripRequest(FrozenModel):
    origin: Place
    destination: Place
    departure_time: datetime
    load_weight_lb: int
    checkpoint_spacing: CheckpointSpacing
    include_rest_breaks: bool = False


class TripPlan(FrozenModel):
    generated_at: datetime
    recommended_route_id: str
    warnings: tuple[PlanWarning, ...]
    routes: tuple[PlannedRoute, ...]
    heatmap: Heatmap

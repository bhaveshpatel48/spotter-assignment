"""Request validation and response shaping: the HTTP boundary only (ADR-0011)."""

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from trip_planning.enums import CheckpointSpacing
from trip_planning.geo import haversine_miles, is_in_contiguous_us
from trip_planning.models import Place, TripRequest

MAX_LOAD_LB = 80_000
MAX_DEPARTURE_AHEAD = timedelta(days=14)
# Allows "leave now" requests that arrive a few minutes after the user picked the time.
PAST_DEPARTURE_TOLERANCE = timedelta(minutes=10)
MIN_TRIP_MILES = 1.0


# --- Requests -----------------------------------------------------------------


class PlaceSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=200)
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)

    def validate(self, attrs):
        if not is_in_contiguous_us(attrs["lat"], attrs["lon"]):
            raise serializers.ValidationError("Location must be in the contiguous United States.")
        return attrs


class PlanRequestSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure_time = serializers.DateTimeField()
    load_weight_lb = serializers.IntegerField(min_value=1, max_value=MAX_LOAD_LB)
    checkpoint_spacing_miles = serializers.ChoiceField(
        choices=[(spacing.value, f"{spacing.value} miles") for spacing in CheckpointSpacing]
    )
    include_rest_breaks = serializers.BooleanField(default=False)

    def validate_departure_time(self, value):
        now = timezone.now()
        if value < now - PAST_DEPARTURE_TOLERANCE:
            raise serializers.ValidationError("Departure time cannot be in the past.")
        if value > now + MAX_DEPARTURE_AHEAD:
            raise serializers.ValidationError("Departure time must be within the next 14 days.")
        return value

    def validate(self, attrs):
        origin, destination = Place(**attrs["origin"]), Place(**attrs["destination"])
        if haversine_miles(origin.coordinate, destination.coordinate) < MIN_TRIP_MILES:
            raise serializers.ValidationError(
                "Origin and destination must be at least 1 mile apart."
            )
        return attrs

    def to_trip_request(self) -> TripRequest:
        data = self.validated_data
        return TripRequest(
            origin=Place(**data["origin"]),
            destination=Place(**data["destination"]),
            departure_time=data["departure_time"],
            load_weight_lb=data["load_weight_lb"],
            checkpoint_spacing=CheckpointSpacing(data["checkpoint_spacing_miles"]),
            include_rest_breaks=data["include_rest_breaks"],
        )


class GeocodeQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=3, max_length=100)


# --- Responses ----------------------------------------------------------------


class GeometryField(serializers.Field):
    """Coordinates as GeoJSON [lon, lat] pairs, rounded to ~1 m to keep responses small."""

    def to_representation(self, value):
        return [[round(c.lon, 5), round(c.lat, 5)] for c in value]


class IntListField(serializers.Field):
    def to_representation(self, value):
        return list(value)


class RiskLevelField(serializers.Field):
    def to_representation(self, value):
        return value.name


class PlaceResponseSerializer(serializers.Serializer):
    label = serializers.CharField()
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class GeocodeResponseSerializer(serializers.Serializer):
    results = PlaceResponseSerializer(many=True)


class WeatherSerializer(serializers.Serializer):
    wind_mph = serializers.FloatField()
    gust_mph = serializers.FloatField()
    rain_in_hr = serializers.FloatField()
    snow_in_hr = serializers.FloatField()


class CheckpointSerializer(serializers.Serializer):
    index = serializers.IntegerField()
    mile = serializers.FloatField()
    lat = serializers.FloatField(source="coordinate.lat")
    lon = serializers.FloatField(source="coordinate.lon")
    eta = serializers.DateTimeField()
    weather = WeatherSerializer()
    risk_level = RiskLevelField(source="risk.level")
    risk_reasons = serializers.ListField(child=serializers.CharField(), source="risk.reasons")


class RouteSummarySerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    travel_time_seconds = serializers.IntegerField(source="travel_time_s")
    departure_time = serializers.DateTimeField()
    arrival_time = serializers.DateTimeField()
    miles_by_risk = serializers.SerializerMethodField()
    average_risk = serializers.FloatField()

    def get_miles_by_risk(self, summary):
        return {level.name: miles for level, miles in summary.miles_by_risk.items()}


class PlannedRouteSerializer(serializers.Serializer):
    id = serializers.CharField()
    rank = serializers.IntegerField()
    is_recommended = serializers.BooleanField()
    summary = RouteSummarySerializer()
    geometry = GeometryField()
    checkpoints = CheckpointSerializer(many=True)


class HeatmapPointSerializer(serializers.Serializer):
    lat = serializers.FloatField(source="coordinate.lat")
    lon = serializers.FloatField(source="coordinate.lon")
    risk = IntListField()


class HeatmapSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField()
    hours = serializers.IntegerField()
    cell_size_deg = serializers.FloatField()
    points = HeatmapPointSerializer(many=True)


class PlanWarningSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()


class PlanResponseSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    recommended_route_id = serializers.CharField()
    warnings = PlanWarningSerializer(many=True)
    routes = PlannedRouteSerializer(many=True)
    heatmap = HeatmapSerializer()

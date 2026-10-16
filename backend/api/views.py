import time

import structlog
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import (
    GeocodeQuerySerializer,
    GeocodeResponseSerializer,
    PlanRequestSerializer,
    PlanResponseSerializer,
)
from core.events import EventName
from providers import open_meteo, tomtom
from trip_planning.service import plan_trip

logger = structlog.get_logger(__name__)


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class GeocodeView(APIView):
    def get(self, request):
        query = GeocodeQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        places = tomtom.geocode(query.validated_data["q"])
        return Response(GeocodeResponseSerializer({"results": places}).data)


class PlanView(APIView):
    def post(self, request):
        serializer = PlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip = serializer.to_trip_request()
        logger.info(
            EventName.PLAN_REQUESTED,
            spacing=int(trip.checkpoint_spacing),
            load_lb=trip.load_weight_lb,
            rest_breaks=trip.include_rest_breaks,
        )

        started = time.perf_counter()
        plan = plan_trip(
            trip,
            fetch_routes=tomtom.calculate_routes,
            fetch_forecasts=open_meteo.get_hourly_forecasts,
            now=timezone.now(),
        )
        logger.info(
            EventName.PLAN_COMPLETED,
            route_count=len(plan.routes),
            recommended_route=plan.recommended_route_id,
            checkpoint_count=sum(len(route.checkpoints) for route in plan.routes),
            heatmap_points=len(plan.heatmap.points),
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
        return Response(PlanResponseSerializer(plan).data)

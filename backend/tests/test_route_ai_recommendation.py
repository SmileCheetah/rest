import unittest
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.schemas.route import Coordinate, RoutePathPoint, RouteSegmentResponse
from app.schemas.weather import ForecastWeatherResponse
from app.services.rest_weather import RestWeatherResult
from app.services.routes import _find_shortest_safe_route, _should_recommend_safe_route
from app.services.tmap import PedestrianRoute


SEOUL_TZ = ZoneInfo("Asia/Seoul")


def _normal_route() -> RouteSegmentResponse:
    return RouteSegmentResponse(
        route_segment_id=1,
        route_option_id=1,
        work_session_id=1,
        schedule_id=1,
        route_type="NORMAL",
        origin=Coordinate(latitude=37.5739, longitude=127.0105),
        destination=Coordinate(latitude=37.5736, longitude=127.0099),
        departure_time=datetime(2026, 8, 19, 14, 0, tzinfo=SEOUL_TZ),
        distance_meters=800,
        walking_minutes=15,
        estimated_arrival_time=datetime(2026, 8, 19, 14, 15, tzinfo=SEOUL_TZ),
        path=[],
    )


def _weather() -> ForecastWeatherResponse:
    return ForecastWeatherResponse(
        latitude=37.5736,
        longitude=127.0099,
        forecast_at=datetime(2026, 8, 19, 14, 0, tzinfo=SEOUL_TZ),
        temperature=32,
        humidity=70,
        apparent_temperature=35,
    )


class RouteAiRecommendationTest(unittest.IsolatedAsyncioTestCase):
    async def test_route_ai_receives_full_accumulated_exposure_context(self):
        captured = {}

        async def resolve(request):
            return RestWeatherResult(request=request, source="REQUEST_FALLBACK", wbgt=28)

        def predict(_service, request, _wbgt):
            captured["request"] = request
            return {"probabilities": {}, "decision": "REST_BEFORE_NEXT_VISIT"}

        with (
            patch("app.services.routes.resolve_rest_weather", new=resolve),
            patch(
                "app.services.routes.RestDecisionService.predict_model_status",
                new=predict,
            ),
        ):
            result = await _should_recommend_safe_route(
                normal_route=_normal_route(),
                weather=_weather(),
                model_weather={"wind_speed": 1.0, "solar_radiation": None, "surface_pressure": None},
                current_continuous_exposure_minutes=0,
                current_total_walking_minutes=30,
                minutes_since_last_rest=110,
                nearest_cooling_spot_distance_meters=180,
            )

        self.assertTrue(result)
        self.assertEqual(captured["request"].total_walking_minutes, 45)
        self.assertEqual(captured["request"].minutes_since_last_rest, 110)

    async def test_shortest_actual_walking_route_wins_over_nearest_origin_spot(self):
        origin = Coordinate(latitude=37.5739, longitude=127.0105, name="현재 위치")
        destination = Coordinate(latitude=37.5736, longitude=127.0099, name="방문지")
        near_origin = SimpleNamespace(
            id=1,
            name="출발지 가까운 쉼터",
            latitude=Decimal("37.5738"),
            longitude=Decimal("127.0104"),
        )
        shorter_total = SimpleNamespace(
            id=2,
            name="총 경로 최단 쉼터",
            latitude=Decimal("37.5737"),
            longitude=Decimal("127.0100"),
        )

        async def route_between(start, end):
            minutes = {
                ("현재 위치", "출발지 가까운 쉼터"): 1,
                ("출발지 가까운 쉼터", "방문지"): 10,
                ("현재 위치", "총 경로 최단 쉼터"): 4,
                ("총 경로 최단 쉼터", "방문지"): 2,
            }[(start.name, end.name)]
            return PedestrianRoute(
                distance_meters=minutes * 80,
                walking_minutes=minutes,
                path=[
                    RoutePathPoint(latitude=start.latitude, longitude=start.longitude),
                    RoutePathPoint(latitude=end.latitude, longitude=end.longitude),
                ],
            )

        with patch("app.services.routes.get_pedestrian_route", new=route_between):
            result = await _find_shortest_safe_route(
                origin,
                destination,
                [near_origin, shorter_total],
                normal_walking_minutes=5,
                max_additional_minutes=5,
            )

        self.assertIsNotNone(result)
        self.assertEqual(result[0].name, "총 경로 최단 쉼터")

    async def test_route_over_detour_limit_is_excluded(self):
        origin = Coordinate(latitude=37.5739, longitude=127.0105, name="현재 위치")
        destination = Coordinate(latitude=37.5736, longitude=127.0099, name="방문지")
        spot = SimpleNamespace(
            id=1,
            name="우회가 긴 쉼터",
            latitude=Decimal("37.5738"),
            longitude=Decimal("127.0104"),
        )

        async def route_between(start, end):
            return PedestrianRoute(
                distance_meters=500,
                walking_minutes=5,
                path=[
                    RoutePathPoint(latitude=start.latitude, longitude=start.longitude),
                    RoutePathPoint(latitude=end.latitude, longitude=end.longitude),
                ],
            )

        with patch("app.services.routes.get_pedestrian_route", new=route_between):
            result = await _find_shortest_safe_route(
                origin,
                destination,
                [spot],
                normal_walking_minutes=3,
                max_additional_minutes=5,
            )

        self.assertIsNone(result)

    async def test_movable_ai_result_does_not_create_safe_route(self):
        async def resolve(request):
            return RestWeatherResult(request=request, source="REQUEST_FALLBACK", wbgt=25)

        with (
            patch("app.services.routes.resolve_rest_weather", new=resolve),
            patch(
                "app.services.routes.RestDecisionService.predict_model_status",
                return_value={"probabilities": {}, "decision": "MOVABLE"},
            ),
        ):
            result = await _should_recommend_safe_route(
                normal_route=_normal_route(),
                weather=_weather(),
                model_weather={"wind_speed": 1.0, "solar_radiation": None, "surface_pressure": None},
                current_continuous_exposure_minutes=10,
                nearest_cooling_spot_distance_meters=180,
            )

        self.assertFalse(result)

    async def test_rest_ai_result_creates_safe_route(self):
        async def resolve(request):
            return RestWeatherResult(request=request, source="REQUEST_FALLBACK", wbgt=28)

        with (
            patch("app.services.routes.resolve_rest_weather", new=resolve),
            patch(
                "app.services.routes.RestDecisionService.predict_model_status",
                return_value={
                    "probabilities": {},
                    "decision": "REST_BEFORE_NEXT_VISIT",
                },
            ),
        ):
            result = await _should_recommend_safe_route(
                normal_route=_normal_route(),
                weather=_weather(),
                model_weather={"wind_speed": 1.0, "solar_radiation": None, "surface_pressure": None},
                current_continuous_exposure_minutes=40,
                nearest_cooling_spot_distance_meters=180,
            )

        self.assertTrue(result)

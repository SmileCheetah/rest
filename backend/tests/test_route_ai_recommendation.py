import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.schemas.route import Coordinate, RouteSegmentResponse
from app.schemas.weather import ForecastWeatherResponse
from app.services.rest_weather import RestWeatherResult
from app.services.routes import _should_recommend_safe_route


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

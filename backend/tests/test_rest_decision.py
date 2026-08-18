import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.rest_decision import RestDecision, RestDecisionRequest
from app.services.rest_decision import RestDecisionService
from app.services.rest_need import calculate_rest_need, classify_rest_need
from app.services.rest_weather import RestWeatherResult
from app.schemas.asos import AsosHourlyObservation, AsosHourlyResponse
from app.services.rest_weather import resolve_rest_weather
from app.services.asos import AsosProviderError

SEOUL_TZ = ZoneInfo("Asia/Seoul")
client = TestClient(app)


def _request(**overrides) -> RestDecisionRequest:
    values = {
        "continuousWalkingMinutes": 27,
        "totalWalkingMinutes": 82,
        "minutesSinceLastRest": 50,
        "recentRestMinutes": 0,
        "temperature": 34.5,
        "humidity": 68,
        "windSpeed": 1.5,
        "observedAt": datetime(2026, 8, 18, 14, tzinfo=SEOUL_TZ),
        "nextTravelMinutes": 18,
        "coolingSpotNearby": True,
        "distanceToCoolingSpotMeters": 180,
        "heatLevel": "HIGH",
    }
    values.update(overrides)
    return RestDecisionRequest.model_validate(values)


class RestDecisionTest(unittest.IsolatedAsyncioTestCase):
    def test_score_is_deterministic_and_exposes_components(self):
        first = calculate_rest_need(_request())
        second = calculate_rest_need(_request())

        self.assertEqual(first, second)
        self.assertGreaterEqual(first.score, 0)
        self.assertLessEqual(first.score, 100)
        self.assertEqual(first.details.heat_score, 90.0)

    def test_level_boundaries_are_explicit(self):
        self.assertEqual(classify_rest_need(39), "LOW")
        self.assertEqual(classify_rest_need(40), "MEDIUM")
        self.assertEqual(classify_rest_need(69), "MEDIUM")
        self.assertEqual(classify_rest_need(70), "HIGH")

    async def test_fallback_recommends_rest_for_high_score(self):
        with patch("app.services.rest_decision.settings.rest_decision_ai_url", None):
            decision, source = await RestDecisionService().decide(
                _request(continuousWalkingMinutes=60, totalWalkingMinutes=180),
                calculate_rest_need(
                    _request(continuousWalkingMinutes=60, totalWalkingMinutes=180)
                ),
            )

        self.assertEqual(source, "FALLBACK")
        self.assertTrue(decision.should_rest)
        self.assertIn(decision.rest_timing, {"NOW", "AFTER_NEXT_VISIT"})

    async def test_ai_result_is_validated_by_high_score_safety_rule(self):
        request = _request(continuousWalkingMinutes=60, totalWalkingMinutes=180)
        score = calculate_rest_need(request)
        ai_response = RestDecision(
            shouldRest=False,
            restTiming="NOT_NEEDED",
            recommendation="move",
            reason="low",
            recommendedRestMinutes=0,
        )
        with (
            patch("app.services.rest_decision.settings.rest_decision_ai_url", "https://ai.test"),
            patch.object(
                RestDecisionService,
                "request_ai_decision",
                new=AsyncMock(return_value=ai_response),
            ),
        ):
            decision, source = await RestDecisionService().decide(request, score)

        self.assertEqual(source, "AI")
        self.assertTrue(decision.should_rest)

    async def test_rest_weather_uses_kma_asos_observation(self):
        request = _request(temperature=20, humidity=20)
        observation = AsosHourlyObservation(
            station_id=108,
            station_name="서울",
            observed_at=request.observed_at,
            temperature=31.2,
            humidity=72,
            wind_speed=1.8,
        )
        response = AsosHourlyResponse(
            station_id=108,
            station_name="서울",
            start_at=request.observed_at,
            end_at=request.observed_at,
            observations=[observation],
        )
        with patch(
            "app.services.rest_weather.get_asos_hourly",
            new=AsyncMock(return_value=response),
        ):
            result = await resolve_rest_weather(request)

        self.assertEqual(result.source, "KMA_ASOS")
        self.assertEqual(result.request.temperature, 31.2)
        self.assertEqual(result.request.humidity, 72)

    async def test_rest_weather_uses_request_weather_when_asos_is_unavailable(self):
        request = _request(temperature=31, humidity=70, wbgt=None)
        with patch(
            "app.services.rest_weather.get_asos_hourly",
            new=AsyncMock(side_effect=AsosProviderError("temporary failure")),
        ):
            result = await resolve_rest_weather(request)

        self.assertEqual(result.source, "REQUEST_FALLBACK")
        self.assertIsNotNone(result.wbgt)
        self.assertGreater(result.wbgt, 0)

    def test_api_accepts_camel_case_and_returns_debug_details(self):
        with patch(
            "app.routers.rest_decision.resolve_rest_weather",
            new=AsyncMock(
                return_value=RestWeatherResult(
                    request=_request(
                        continuousWalkingMinutes=10,
                        totalWalkingMinutes=30,
                        minutesSinceLastRest=10,
                        recentRestMinutes=20,
                        temperature=24,
                        humidity=50,
                        windSpeed=2,
                        nextTravelMinutes=5,
                        coolingSpotNearby=False,
                    ),
                    source="KMA_ASOS",
                )
            ),
        ):
            response = client.post(
                "/rest/decision",
                json={
                    "continuousWalkingMinutes": 10,
                    "totalWalkingMinutes": 30,
                    "minutesSinceLastRest": 10,
                    "recentRestMinutes": 20,
                    "temperature": 24,
                    "humidity": 50,
                    "windSpeed": 2,
                    "observedAt": "2026-08-18T14:00:00+09:00",
                    "nextTravelMinutes": 5,
                    "coolingSpotNearby": False,
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["restNeedScore"])
        self.assertIsNone(payload["details"])
        self.assertIn("shouldRest", payload["decision"])
        self.assertEqual(payload["decisionSource"], "FALLBACK")
        self.assertEqual(payload["weatherSource"], "KMA_ASOS")

    def test_api_uses_local_rest_status_model_when_wbgt_is_available(self):
        with (
            patch(
                "app.routers.rest_decision.resolve_rest_weather",
                new=AsyncMock(
                    return_value=RestWeatherResult(
                        request=_request(wbgt=27, distanceToCoolingSpotMeters=350),
                        source="KMA_ASOS",
                    )
                ),
            ),
            patch.object(
                RestDecisionService,
                "predict_model_status",
                return_value={
                    "probabilities": {
                        "MOVABLE": 0.05,
                        "REST_RECOMMENDED": 0.25,
                        "REST_BEFORE_NEXT_VISIT": 0.70,
                    },
                    "decision": "REST_BEFORE_NEXT_VISIT",
                },
            ),
        ):
            response = client.post(
                "/rest/decision",
                json={
                    "continuousWalkingMinutes": 72,
                    "totalWalkingMinutes": 82,
                    "minutesSinceLastRest": 80,
                    "recentRestMinutes": 0,
                    "temperature": 30,
                    "humidity": 70,
                    "wbgt": 27,
                    "observedAt": "2026-08-18T14:00:00+09:00",
                    "nextTravelMinutes": 23,
                    "coolingSpotNearby": False,
                    "distanceToCoolingSpotMeters": 350,
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["decisionSource"], "MODEL")
        self.assertEqual(payload["restStatusPrediction"]["decision"], "REST_BEFORE_NEXT_VISIT")
        self.assertTrue(payload["decision"]["shouldRest"])


if __name__ == "__main__":
    unittest.main()

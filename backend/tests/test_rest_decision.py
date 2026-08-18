import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.rest_decision import RestDecision, RestDecisionRequest
from app.services.rest_decision import RestDecisionService
from app.services.rest_need import calculate_rest_need, classify_rest_need

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

    def test_api_accepts_camel_case_and_returns_debug_details(self):
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
        self.assertIn("restNeedScore", payload)
        self.assertIn("walkingScore", payload["details"])
        self.assertIn("shouldRest", payload["decision"])
        self.assertEqual(payload["decisionSource"], "FALLBACK")


if __name__ == "__main__":
    unittest.main()

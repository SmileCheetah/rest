import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app
from app.models.risk_assessment import RiskAssessment
from app.schemas.risk_analysis import RiskEvaluateRequest
from app.services.exposure import ExposureState, update_exposure
from app.services.risk_analysis import evaluate_risk

SEOUL_TZ = ZoneInfo("Asia/Seoul")
client = TestClient(app)


class RiskAnalysisTest(unittest.TestCase):
    def test_high_heat_requires_rest(self):
        result = evaluate_risk(RiskEvaluateRequest(
            route_option_id=1, temperature=38, humidity=70,
            observed_at=datetime(2026, 8, 18, 14, 0, tzinfo=SEOUL_TZ),
            walking_minutes=20,
            current_continuous_exposure_minutes=20,
            expected_continuous_exposure_minutes=40,
        ))
        self.assertEqual(result.risk_level, "REST_REQUIRED")
        self.assertTrue(result.rest_required)
        self.assertEqual(result.recommended_rest_count, 1)
        self.assertEqual(result.apparent_temperature, 39.5)
        self.assertNotIn("risk_score", result.model_dump())
        self.assertIn("다음 방문 전 휴식이 필요합니다.", result.reason_message)

    def test_normal_conditions_allow_movement(self):
        result = evaluate_risk(RiskEvaluateRequest(
            route_option_id=1, temperature=25, humidity=50,
            observed_at=datetime(2026, 8, 18, 14, 0, tzinfo=SEOUL_TZ),
            walking_minutes=10,
            current_continuous_exposure_minutes=0,
            expected_continuous_exposure_minutes=10,
        ))
        self.assertEqual(result.risk_level, "MOVE_POSSIBLE")
        self.assertFalse(result.rest_required)
        self.assertEqual(result.recommended_rest_count, 0)

    def test_calculates_winter_apparent_temperature_before_classification(self):
        result = evaluate_risk(RiskEvaluateRequest(
            route_option_id=1, temperature=0, humidity=50,
            observed_at=datetime(2026, 1, 10, 8, 0, tzinfo=SEOUL_TZ),
            wind_speed=5,
            walking_minutes=10,
            current_continuous_exposure_minutes=0,
            expected_continuous_exposure_minutes=10,
        ))
        self.assertEqual(result.apparent_temperature, -4.9)
        self.assertEqual(result.risk_level, "MOVE_POSSIBLE")

    def test_high_apparent_temperature_recommends_rest(self):
        result = evaluate_risk(RiskEvaluateRequest(
            route_option_id=2, temperature=34.5, humidity=68,
            observed_at=datetime(2026, 8, 18, 14, 0, tzinfo=SEOUL_TZ),
            walking_minutes=18,
            current_continuous_exposure_minutes=10,
            expected_continuous_exposure_minutes=28,
        ))
        self.assertEqual(result.apparent_temperature, 35.7)
        self.assertEqual(result.risk_level, "REST_RECOMMENDED")
        self.assertFalse(result.rest_required)
        self.assertEqual(result.recommended_rest_count, 1)
        self.assertIn("HIGH_APPARENT_TEMPERATURE", result.reason_codes)
        self.assertIn("이동 전후 휴식을 권장합니다.", result.reason_message)

    def test_long_continuous_exposure_recommends_rest(self):
        result = evaluate_risk(RiskEvaluateRequest(
            route_option_id=3, temperature=25, humidity=50,
            observed_at=datetime(2026, 8, 18, 14, 0, tzinfo=SEOUL_TZ),
            walking_minutes=20,
            current_continuous_exposure_minutes=20,
            expected_continuous_exposure_minutes=40,
        ))
        self.assertEqual(result.risk_level, "REST_RECOMMENDED")
        self.assertIn("LONG_CONTINUOUS_EXPOSURE", result.reason_codes)
        self.assertIn("예상 연속 야외 노출 40분", result.reason_message)

    def test_twenty_minute_rest_resets_continuous_exposure(self):
        state, completed, _ = update_exposure(
            ExposureState(continuous_exposure_minutes=45),
            "RESTING", 20, False,
        )
        self.assertTrue(completed)
        self.assertEqual(state.continuous_exposure_minutes, 0)

    def test_api_response_excludes_risk_score(self):
        response = client.post("/risk/evaluate", json={
            "route_option_id": 2,
            "temperature": 34.5,
            "humidity": 68,
            "observed_at": "2026-08-18T14:00:00+09:00",
            "wind_speed": 1.5,
            "walking_minutes": 18,
            "current_continuous_exposure_minutes": 25,
            "expected_continuous_exposure_minutes": 43,
            "shelter_accessibility": 0.6,
        })

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn("risk_score", payload)
        self.assertNotIn("riskScore", payload)
        self.assertEqual(payload["risk_level"], "REST_RECOMMENDED")
        self.assertEqual(payload["recommended_rest_count"], 1)

    def test_persistence_model_excludes_risk_score(self):
        self.assertNotIn("risk_score", RiskAssessment.__table__.columns)


if __name__ == "__main__":
    unittest.main()

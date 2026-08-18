import unittest

from app.schemas.risk_analysis import RiskEvaluateRequest
from app.services.exposure import ExposureState, update_exposure
from app.services.risk_analysis import evaluate_risk


class RiskAnalysisTest(unittest.TestCase):
    def test_high_heat_requires_rest(self):
        result = evaluate_risk(RiskEvaluateRequest(
            route_option_id=1, temperature=34, humidity=70,
            apparent_temperature=38, walking_minutes=20,
            current_continuous_exposure_minutes=20,
            expected_continuous_exposure_minutes=40,
        ))
        self.assertEqual(result.risk_level, "REST_REQUIRED")
        self.assertEqual(result.recommended_rest_count, 1)

    def test_normal_conditions_are_safe(self):
        result = evaluate_risk(RiskEvaluateRequest(
            route_option_id=1, temperature=25, humidity=50,
            apparent_temperature=26, walking_minutes=10,
            current_continuous_exposure_minutes=0,
            expected_continuous_exposure_minutes=10,
        ))
        self.assertEqual(result.risk_level, "SAFE")

    def test_twenty_minute_rest_resets_continuous_exposure(self):
        state, completed, _ = update_exposure(
            ExposureState(continuous_exposure_minutes=45),
            "RESTING", 20, False,
        )
        self.assertTrue(completed)
        self.assertEqual(state.continuous_exposure_minutes, 0)


if __name__ == "__main__":
    unittest.main()

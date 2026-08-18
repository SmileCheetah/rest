import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.exposure import ExposureState
from app.services.risk_features import build_route_risk_features


SEOUL_TZ = ZoneInfo("Asia/Seoul")


class RiskFeaturesTest(unittest.TestCase):
    def test_builds_model_ready_route_features(self) -> None:
        result = build_route_risk_features(
            weather_at=datetime(2026, 8, 18, 13, 0, tzinfo=SEOUL_TZ),
            temperature=34.5,
            humidity=68,
            wind_speed=2.0,
            walking_minutes=18,
            current_state=ExposureState(
                continuous_exposure_minutes=25,
                daily_exposure_minutes=80,
                daily_rest_minutes=20,
            ),
            projected_state=ExposureState(
                continuous_exposure_minutes=43,
                daily_exposure_minutes=98,
                daily_rest_minutes=20,
            ),
        )

        self.assertEqual(result.temperature, 34.5)
        self.assertEqual(result.current_continuous_exposure_minutes, 25)
        self.assertEqual(result.expected_continuous_exposure_minutes, 43)
        self.assertEqual(result.expected_daily_exposure_minutes, 98)


if __name__ == "__main__":
    unittest.main()

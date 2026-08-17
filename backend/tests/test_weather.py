import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.weather import (
    _latest_ultra_nowcast_base,
    _latest_village_forecast_base,
    calculate_apparent_temperature,
    latitude_longitude_to_grid,
)

SEOUL_TZ = ZoneInfo("Asia/Seoul")


class WeatherServiceTest(unittest.TestCase):
    def test_converts_seoul_coordinates_to_kma_grid(self) -> None:
        self.assertEqual(latitude_longitude_to_grid(37.5665, 126.9780), (60, 127))

    def test_uses_previous_nowcast_before_api_release(self) -> None:
        now = datetime(2026, 8, 18, 10, 30, tzinfo=SEOUL_TZ)
        self.assertEqual(
            _latest_ultra_nowcast_base(now),
            datetime(2026, 8, 18, 9, 0, tzinfo=SEOUL_TZ),
        )

    def test_uses_previous_day_forecast_before_first_release(self) -> None:
        now = datetime(2026, 8, 18, 1, 30, tzinfo=SEOUL_TZ)
        self.assertEqual(
            _latest_village_forecast_base(now),
            datetime(2026, 8, 17, 23, 0, tzinfo=SEOUL_TZ),
        )

    def test_calculates_summer_apparent_temperature(self) -> None:
        observed_at = datetime(2026, 8, 18, 14, 0, tzinfo=SEOUL_TZ)
        apparent = calculate_apparent_temperature(34.0, 72.0, observed_at)
        self.assertGreater(apparent, 34.0)
        self.assertLess(apparent, 40.0)


if __name__ == "__main__":
    unittest.main()

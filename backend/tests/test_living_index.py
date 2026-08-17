import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.living_index import (
    _latest_living_index_base,
    _select_index_value,
    air_diffusion_label,
    ultraviolet_label,
)

SEOUL_TZ = ZoneInfo("Asia/Seoul")


class LivingIndexServiceTest(unittest.TestCase):
    def test_uses_previous_evening_before_morning_release(self) -> None:
        now = datetime(2026, 8, 18, 1, 0, tzinfo=SEOUL_TZ)
        self.assertEqual(
            _latest_living_index_base(now),
            datetime(2026, 8, 17, 18, 0, tzinfo=SEOUL_TZ),
        )

    def test_selects_prediction_nearest_to_current_time(self) -> None:
        item = {"date": "2026081718", "h3": "2", "h6": "4", "h9": "7"}
        now = datetime(2026, 8, 18, 0, 20, tzinfo=SEOUL_TZ)
        result = _select_index_value(item, now, "uv")
        self.assertEqual(result.value, 4)
        self.assertEqual(result.label, "보통")

    def test_labels_official_index_ranges(self) -> None:
        self.assertEqual(ultraviolet_label(8), "매우 높음")
        self.assertEqual(air_diffusion_label(75), "높음")


if __name__ == "__main__":
    unittest.main()

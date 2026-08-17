import unittest
from datetime import date

from app.services.heatwave import _to_category_forecasts, normalize_heatwave_level


class HeatwaveServiceTest(unittest.TestCase):
    def test_normalizes_official_levels(self) -> None:
        self.assertEqual(normalize_heatwave_level("주의"), ("CAUTION", "주의"))
        self.assertEqual(normalize_heatwave_level("위험"), ("DANGER", "위험"))

    def test_filters_old_and_other_region_forecasts(self) -> None:
        items = [
            {"regId": "11B10101", "tmEf": "20260818", "clsfc": "산업", "value": "경고"},
            {"regId": "11B10101", "tmEf": "20260817", "clsfc": "산업", "value": "주의"},
            {"regId": "11B20201", "tmEf": "20260818", "clsfc": "산업", "value": "위험"},
        ]
        result = _to_category_forecasts(items, date(2026, 8, 18))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].level, "WARNING")


if __name__ == "__main__":
    unittest.main()

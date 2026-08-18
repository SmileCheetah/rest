import unittest

from app.ml.heat_risk import (
    HeatRiskConfig,
    calculate_initial_risk_score,
    generate_synthetic_data,
    get_risk_level,
)


class HeatRiskTest(unittest.TestCase):
    def test_rule_score_uses_wbgt_boundaries(self):
        common = {
            "continuous_exposure_minutes": 0,
            "next_travel_minutes": 0,
            "time_since_rest_minutes": 0,
            "cooling_spot_distance_m": 0,
        }
        self.assertEqual(calculate_initial_risk_score(wbgt=20, **common), 0)
        self.assertEqual(calculate_initial_risk_score(wbgt=22.9, **common), 10)
        self.assertEqual(calculate_initial_risk_score(wbgt=23, **common), 20)
        self.assertEqual(calculate_initial_risk_score(wbgt=25, **common), 35)
        self.assertEqual(calculate_initial_risk_score(wbgt=27.9, **common), 35)
        self.assertEqual(calculate_initial_risk_score(wbgt=28, **common), 50)

    def test_risk_level_boundaries(self):
        self.assertEqual(get_risk_level(29), "LOW")
        self.assertEqual(get_risk_level(30), "CAUTION")
        self.assertEqual(get_risk_level(50), "REST_RECOMMENDED")
        self.assertEqual(get_risk_level(70), "REST_REQUIRED")
        self.assertEqual(get_risk_level(85), "IMMEDIATE_REST")

    def test_synthetic_data_is_reproducible_and_bounded(self):
        config = HeatRiskConfig(sample_count=100, add_noise=False)
        first = generate_synthetic_data(config)
        second = generate_synthetic_data(config)
        self.assertTrue(first.equals(second))
        self.assertEqual(len(first), 100)
        self.assertGreaterEqual(first["heat_risk_score"].min(), 0)
        self.assertLessEqual(first["heat_risk_score"].max(), 100)
        self.assertEqual(set(first.columns), {
            "wbgt",
            "continuous_exposure_minutes",
            "next_travel_minutes",
            "time_since_rest_minutes",
            "cooling_spot_distance_m",
            "heat_risk_score",
            "risk_level",
        })


if __name__ == "__main__":
    unittest.main()

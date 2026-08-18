import unittest

from app.ml.risk_modeling import (
    compare_models,
    create_synthetic_label,
    generate_synthetic_dataset,
    moderate_work_limit_minutes,
)
from app.ml.work_limit_modeling import (
    compare_work_limit_models,
    work_limit_label,
)


class RiskModelingTest(unittest.TestCase):
    def test_moderate_work_limits_become_stricter_as_wbgt_rises(self):
        self.assertIsNone(moderate_work_limit_minutes(24.9))
        self.assertEqual(moderate_work_limit_minutes(26.7), 45)
        self.assertEqual(moderate_work_limit_minutes(27.0), 45)
        self.assertEqual(moderate_work_limit_minutes(30.0), 15)
        self.assertEqual(moderate_work_limit_minutes(31.1), 0)

    def test_label_requires_rest_after_current_limit_is_reached(self):
        label = create_synthetic_label(
            estimated_wbgt=28.5,
            current_continuous_exposure_minutes=30,
            expected_continuous_exposure_minutes=45,
        )
        self.assertEqual(label, "REST_REQUIRED")

    def test_label_does_not_invent_a_low_wbgt_exposure_limit(self):
        label = create_synthetic_label(
            estimated_wbgt=26.6,
            current_continuous_exposure_minutes=180,
            expected_continuous_exposure_minutes=200,
        )
        self.assertEqual(label, "MOVE_POSSIBLE")

    def test_compares_all_three_classifiers_on_one_split(self):
        dataset = generate_synthetic_dataset(
            weather_samples=120,
            scenarios_per_weather=3,
            seed=7,
        )
        comparison = compare_models(dataset, seed=7)

        self.assertTrue(
            {
                "rule_classifier",
                "random_forest",
                "hist_gradient_boosting",
            }.issubset(comparison.report["models"]),
        )
        self.assertIn(
            comparison.best_model_name,
            {
                "random_forest_tuned",
                "hist_gradient_boosting_tuned",
            },
        )
        self.assertIn("permutation_importance", comparison.report["tuning"])
        self.assertGreater(len(comparison.selected_feature_names), 0)
        self.assertEqual(
            list(comparison.selected_feature_names),
            comparison.report["feature_selection"]["selected_features"],
        )
        self.assertGreater(comparison.report["split"]["train_rows"], 0)
        self.assertGreater(comparison.report["split"]["test_rows"], 0)
        self.assertNotIn("current_daily_exposure_minutes", comparison.report["feature_names"])
        self.assertNotIn("current_daily_rest_minutes", comparison.report["feature_names"])

    def test_work_limit_labels_follow_wbgt_table(self):
        self.assertEqual(work_limit_label(25.0), "WORK_60")
        self.assertEqual(work_limit_label(27.0), "WORK_45")
        self.assertEqual(work_limit_label(28.5), "WORK_30")
        self.assertEqual(work_limit_label(30.0), "WORK_15")
        self.assertEqual(work_limit_label(31.1), "REST_REQUIRED")

    def test_compares_models_using_weather_only_for_work_limit(self):
        dataset = generate_synthetic_dataset(
            weather_samples=120,
            scenarios_per_weather=3,
            seed=7,
        )
        comparison = compare_work_limit_models(dataset, seed=7)

        self.assertEqual(
            set(comparison.report["feature_names"]),
            {"temperature", "humidity", "wind_speed", "solar_radiation", "surface_pressure"},
        )
        self.assertEqual(
            set(comparison.report["models"]),
            {"random_forest", "hist_gradient_boosting"},
        )
        self.assertIn(
            comparison.best_model_name,
            {"random_forest", "hist_gradient_boosting"},
        )


if __name__ == "__main__":
    unittest.main()

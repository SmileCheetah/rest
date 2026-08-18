import unittest
from pathlib import Path

from app.ml.heat_risk import HeatRiskConfig
from app.ml.rest_status_classifier import (
    STATUS_LABELS,
    assign_rest_status,
    generate_rest_status_data,
)


class RestStatusClassifierTest(unittest.TestCase):
    def test_status_boundaries(self):
        self.assertEqual(assign_rest_status(39), "MOVABLE")
        self.assertEqual(assign_rest_status(40), "REST_RECOMMENDED")
        self.assertEqual(assign_rest_status(69), "REST_RECOMMENDED")
        self.assertEqual(assign_rest_status(70), "REST_BEFORE_NEXT_VISIT")

    def test_generated_labels_are_three_classes(self):
        frame = generate_rest_status_data(HeatRiskConfig(sample_count=100))
        self.assertEqual(set(frame["rest_status"].unique()), set(STATUS_LABELS))
        self.assertEqual(len(frame), 100)


if __name__ == "__main__":
    unittest.main()

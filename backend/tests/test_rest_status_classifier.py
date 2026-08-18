import unittest
from pathlib import Path

from app.ml.heat_risk import HeatRiskConfig
from app.ml.rest_status_classifier import (
    STATUS_LABELS,
    assign_rest_status,
    generate_rest_status_data,
    load_rest_status_classifier,
    predict_rest_status,
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

    def test_saved_model_covers_three_operational_scenarios(self):
        model_path = (
            Path(__file__).resolve().parents[1]
            / "artifacts/rest-status-model/rest_status_classifier.json"
        )
        self.assertTrue(model_path.exists(), "rest status model artifact is missing")
        model = load_rest_status_classifier(model_path)
        # 실제 4개 일정 계획과 같은 범위(12~21분 이동, 방문지 체류 후
        # 연속 노출 0분, 마지막 Cooling Spot 휴식 후 시간 누적)를 사용합니다.
        scenarios = [
            ("MOVABLE", 27, 0, 12, 0, 350),
            ("REST_RECOMMENDED", 28.17, 0, 12, 0, 350),
            ("REST_BEFORE_NEXT_VISIT", 28.17, 0, 21, 110, 350),
        ]

        for expected, wbgt, exposure, travel, since_rest, distance in scenarios:
            with self.subTest(expected=expected):
                result = predict_rest_status(
                    model=model,
                    wbgt=wbgt,
                    continuous_exposure_minutes=exposure,
                    next_travel_minutes=travel,
                    time_since_rest_minutes=since_rest,
                    cooling_spot_distance_m=distance,
                )
                self.assertEqual(result["decision"], expected)


if __name__ == "__main__":
    unittest.main()

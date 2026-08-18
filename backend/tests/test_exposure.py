import unittest

from app.services.exposure import ExposureEvent, ExposureState, project_exposure


class ExposureServiceTest(unittest.TestCase):
    def test_outdoor_movement_and_visit_accumulate_continuous_exposure(self) -> None:
        result = project_exposure(
            ExposureState(continuous_exposure_minutes=40),
            [
                ExposureEvent(activity_type="MOVING", duration_minutes=20),
                ExposureEvent(activity_type="VISITING", duration_minutes=30),
            ],
        )

        self.assertEqual(result.state.continuous_exposure_minutes, 90)
        self.assertEqual(result.state.daily_exposure_minutes, 50)

    def test_twenty_minute_rest_resets_continuous_exposure(self) -> None:
        result = project_exposure(
            ExposureState(continuous_exposure_minutes=90),
            [ExposureEvent(activity_type="RESTING", duration_minutes=20)],
        )

        self.assertTrue(result.rest_completed)
        self.assertEqual(result.state.continuous_exposure_minutes, 0)
        self.assertEqual(result.state.daily_rest_minutes, 20)

    def test_indoor_visit_does_not_add_outdoor_exposure(self) -> None:
        result = project_exposure(
            ExposureState(continuous_exposure_minutes=40),
            [
                ExposureEvent(
                    activity_type="VISITING",
                    duration_minutes=30,
                    is_outdoor=False,
                )
            ],
        )

        self.assertEqual(result.state.continuous_exposure_minutes, 40)
        self.assertEqual(result.state.daily_exposure_minutes, 0)


if __name__ == "__main__":
    unittest.main()

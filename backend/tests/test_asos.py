import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from app.services.asos import get_asos_hourly


SEOUL_TZ = ZoneInfo("Asia/Seoul")


class AsosServiceTest(unittest.IsolatedAsyncioTestCase):
    @patch("app.services.asos.request_public_data_json", new_callable=AsyncMock)
    async def test_requests_hourly_asos_fields_and_converts_solar_radiation(
        self,
        request_mock: AsyncMock,
    ) -> None:
        request_mock.return_value = {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
                "body": {
                    "items": {
                        "item": [
                            {
                                "stnId": "108",
                                "stnNm": "서울",
                                "tm": "2026-08-18 13",
                                "ta": "34.5",
                                "hm": "68",
                                "ws": "1.5",
                                "icsr": "0.72",
                                "pa": "1008.0",
                                "ps": "1011.2",
                                "td": "27.3",
                            }
                        ]
                    }
                },
            }
        }

        with patch("app.services.asos.settings") as settings_mock:
            settings_mock.kma_asos_api_key = "asos-key"
            settings_mock.kma_api_key = None
            settings_mock.kma_asos_api_base_url = "https://example.test/asos"
            result = await get_asos_hourly(
                108,
                datetime(2026, 8, 18, 13, 0, tzinfo=SEOUL_TZ),
                datetime(2026, 8, 18, 14, 0, tzinfo=SEOUL_TZ),
            )

        request_mock.assert_awaited_once()
        request_url, request_key, request_params = request_mock.await_args.args
        self.assertEqual(
            request_url,
            "https://example.test/asos/getWthrDataList",
        )
        self.assertEqual(request_key, "asos-key")
        self.assertEqual(request_params["dataCd"], "ASOS")
        self.assertEqual(request_params["dateCd"], "HR")
        self.assertEqual(request_params["stnIds"], 108)
        self.assertEqual(result.observations[0].temperature, 34.5)
        self.assertEqual(result.observations[0].surface_pressure, 1008.0)
        self.assertAlmostEqual(result.observations[0].solar_radiation, 200.0)

    @patch("app.services.asos.request_public_data_json", new_callable=AsyncMock)
    async def test_converts_missing_asos_values_to_none(
        self,
        request_mock: AsyncMock,
    ) -> None:
        request_mock.return_value = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {
                    "items": {
                        "item": {
                            "stnId": "108",
                            "stnNm": "서울",
                            "tm": "2026-08-18 13",
                            "ta": "-",
                            "hm": "-",
                            "ws": "-",
                            "icsr": "-",
                            "pa": "-",
                            "ps": "-",
                            "td": "-",
                        }
                    }
                },
            }
        }

        with patch("app.services.asos.settings") as settings_mock:
            settings_mock.kma_asos_api_key = "asos-key"
            settings_mock.kma_asos_api_base_url = "https://example.test/asos"
            result = await get_asos_hourly(
                108,
                datetime(2026, 8, 18, 13),
                datetime(2026, 8, 18, 13),
            )

        observation = result.observations[0]
        self.assertIsNone(observation.temperature)
        self.assertIsNone(observation.solar_radiation)
        self.assertIsNone(observation.surface_pressure)


if __name__ == "__main__":
    unittest.main()

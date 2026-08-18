import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.asos import AsosHourlyObservation, AsosHourlyResponse
from app.services.weather_risk import (
    calculate_weather_risk,
    classify_weather_risk,
    interpolate_score,
    resolve_weather,
)


SEOUL_TZ = ZoneInfo("Asia/Seoul")
client = TestClient(app)


class WeatherRiskTest(unittest.IsolatedAsyncioTestCase):
    def test_wbgt_anchor_interpolation(self):
        self.assertEqual(interpolate_score(18, ((18, 0), (21, 30)))[0], 0)
        self.assertEqual(interpolate_score(23, ((21, 30), (25, 70)))[0], 50)
        self.assertEqual(interpolate_score(35, ((28, 0), (38, 100)))[0], 70)

    def test_weather_risk_level_boundaries(self):
        self.assertEqual(classify_weather_risk(39), "LOW")
        self.assertEqual(classify_weather_risk(40), "MEDIUM")
        self.assertEqual(classify_weather_risk(69), "MEDIUM")
        self.assertEqual(classify_weather_risk(70), "HIGH")

    def test_explicit_wbgt_is_preferred(self):
        result = calculate_weather_risk(
            temperature=35,
            humidity=80,
            wind_speed=None,
            observed_at=datetime(2026, 8, 18, 14, tzinfo=SEOUL_TZ),
            wbgt=25,
            solar_radiation=None,
            surface_pressure=None,
            latitude=None,
            longitude=None,
        )
        self.assertEqual(result[2], "WBGT")
        self.assertEqual(result[0], 70)

    def test_apparent_temperature_is_fallback(self):
        result = calculate_weather_risk(
            temperature=30,
            humidity=70,
            wind_speed=1.5,
            observed_at=datetime(2026, 8, 18, 14, tzinfo=SEOUL_TZ),
            wbgt=None,
            solar_radiation=None,
            surface_pressure=None,
            latitude=None,
            longitude=None,
        )
        self.assertEqual(result[2], "APPARENT_TEMPERATURE")
        self.assertGreaterEqual(result[0], 0)
        self.assertLessEqual(result[0], 100)

    async def test_resolve_weather_prefers_asos(self):
        observed_at = datetime(2026, 8, 18, 14, tzinfo=SEOUL_TZ)
        response = AsosHourlyResponse(
            station_id=108,
            station_name="Seoul",
            start_at=observed_at,
            end_at=observed_at,
            observations=[
                AsosHourlyObservation(
                    station_id=108,
                    station_name="Seoul",
                    observed_at=observed_at,
                    temperature=31,
                    humidity=70,
                    wind_speed=1.5,
                    solar_radiation=500,
                    surface_pressure=1005,
                )
            ],
        )
        with patch(
            "app.services.weather_risk.get_asos_hourly",
            new=AsyncMock(return_value=response),
        ):
            result = await resolve_weather(
                station_id=108,
                observed_at=observed_at,
                temperature=None,
                humidity=None,
                wind_speed=None,
                solar_radiation=None,
                surface_pressure=None,
            )
        self.assertEqual(result.source, "KMA_ASOS")
        self.assertEqual(result.observation.temperature, 31)

    def test_endpoint_returns_weather_risk_schema(self):
        with patch(
            "app.routers.weather_risk.resolve_weather",
            new=AsyncMock(
                return_value=type(
                    "Weather",
                    (),
                    {
                        "source": "REQUEST_FALLBACK",
                        "observation": AsosHourlyObservation(
                            station_id=108,
                            station_name="request",
                            observed_at=datetime(2026, 8, 18, 14, tzinfo=SEOUL_TZ),
                            temperature=30,
                            humidity=70,
                            wind_speed=1.5,
                        ),
                    },
                )(),
            ),
        ):
            response = client.post(
                "/weather-risk/score",
                json={
                    "stationId": 108,
                    "observedAt": "2026-08-18T14:00:00+09:00",
                },
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("weatherRiskScore", payload)
        self.assertIn(payload["weatherRiskLevel"], {"LOW", "MEDIUM", "HIGH"})
        self.assertEqual(payload["weatherSource"], "REQUEST_FALLBACK")


if __name__ == "__main__":
    unittest.main()

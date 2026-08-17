import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import httpx

from app.config import settings
from app.schemas.weather import (
    CurrentWeatherResponse,
    ForecastWeatherResponse,
    HourlyWeatherResponse,
    WeatherValue,
)

SEOUL_TZ = ZoneInfo("Asia/Seoul")


class WeatherConfigurationError(Exception):
    """기상청 API 설정이 없습니다."""


class WeatherProviderError(Exception):
    """기상청 API 요청 또는 응답 처리에 실패했습니다."""


class WeatherForecastNotFoundError(Exception):
    """요청한 시각의 예보를 찾을 수 없습니다."""


def latitude_longitude_to_grid(latitude: float, longitude: float) -> tuple[int, int]:
    """위·경도를 기상청 동네예보 격자 좌표로 변환합니다."""
    earth_radius = 6371.00877
    grid_spacing = 5.0
    standard_latitude_1 = math.radians(30.0)
    standard_latitude_2 = math.radians(60.0)
    reference_longitude = math.radians(126.0)
    reference_latitude = math.radians(38.0)
    reference_x = 43.0
    reference_y = 136.0

    re = earth_radius / grid_spacing
    sn = math.tan(math.pi * 0.25 + standard_latitude_2 * 0.5) / math.tan(
        math.pi * 0.25 + standard_latitude_1 * 0.5
    )
    sn = math.log(math.cos(standard_latitude_1) / math.cos(standard_latitude_2)) / math.log(sn)
    sf = (
        math.tan(math.pi * 0.25 + standard_latitude_1 * 0.5) ** sn
        * math.cos(standard_latitude_1)
        / sn
    )
    ro = re * sf / math.tan(math.pi * 0.25 + reference_latitude * 0.5) ** sn
    ra = re * sf / math.tan(math.pi * 0.25 + math.radians(latitude) * 0.5) ** sn
    theta = math.radians(longitude) - reference_longitude
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    grid_x = int(ra * math.sin(theta) + reference_x + 0.5)
    grid_y = int(ro - ra * math.cos(theta) + reference_y + 0.5)
    return grid_x, grid_y


def calculate_apparent_temperature(
    temperature: float,
    humidity: float,
    observed_at: datetime,
    wind_speed: float | None = None,
) -> float:
    """기상청 계절별 산식으로 체감온도를 계산합니다."""
    if 5 <= observed_at.month <= 9:
        wet_bulb = (
            temperature * math.atan(0.151977 * math.sqrt(humidity + 8.313659))
            + math.atan(temperature + humidity)
            - math.atan(humidity - 1.676331)
            + 0.00391838 * humidity**1.5 * math.atan(0.023101 * humidity)
            - 4.686035
        )
        apparent = (
            -0.2442
            + 0.55399 * wet_bulb
            + 0.45535 * temperature
            - 0.0022 * wet_bulb**2
            + 0.00278 * wet_bulb * temperature
            + 3.0
        )
    elif temperature <= 10 and wind_speed is not None and wind_speed >= 1.3:
        wind_kph = wind_speed * 3.6
        apparent = (
            13.12
            + 0.6215 * temperature
            - 11.37 * wind_kph**0.16
            + 0.3965 * wind_kph**0.16 * temperature
        )
    else:
        apparent = temperature
    return round(apparent, 1)


async def get_current_weather(
    latitude: float,
    longitude: float,
    *,
    now: datetime | None = None,
) -> CurrentWeatherResponse:
    requested_at = _seoul_now(now)
    base_at = _latest_ultra_nowcast_base(requested_at)
    grid_x, grid_y = latitude_longitude_to_grid(latitude, longitude)
    items = await _request_kma(
        "getUltraSrtNcst",
        base_at=base_at,
        grid_x=grid_x,
        grid_y=grid_y,
    )
    values = {str(item["category"]): float(item["obsrValue"]) for item in items}
    try:
        temperature = values["T1H"]
        humidity = values["REH"]
    except KeyError as exc:
        raise WeatherProviderError("current weather fields are missing") from exc

    observed_at = _item_datetime(items[0], "baseDate", "baseTime")
    return CurrentWeatherResponse(
        latitude=latitude,
        longitude=longitude,
        grid_x=grid_x,
        grid_y=grid_y,
        observed_at=observed_at,
        temperature=temperature,
        humidity=humidity,
        apparent_temperature=calculate_apparent_temperature(
            temperature,
            humidity,
            observed_at,
            values.get("WSD"),
        ),
    )


async def get_hourly_weather(
    latitude: float,
    longitude: float,
    forecast_date: date,
    *,
    now: datetime | None = None,
) -> HourlyWeatherResponse:
    forecasts = await _get_short_term_forecasts(
        latitude,
        longitude,
        now=_seoul_now(now),
    )
    selected = [item for item in forecasts if item.forecast_at.date() == forecast_date]
    if not selected:
        raise WeatherForecastNotFoundError("hourly weather not found for requested date")
    return HourlyWeatherResponse(
        latitude=latitude,
        longitude=longitude,
        forecast_date=forecast_date,
        forecasts=selected,
    )


async def get_forecast_weather(
    latitude: float,
    longitude: float,
    forecast_at: datetime,
    *,
    now: datetime | None = None,
) -> ForecastWeatherResponse:
    target = _as_seoul_datetime(forecast_at)
    forecasts = await _get_short_term_forecasts(
        latitude,
        longitude,
        now=_seoul_now(now),
    )
    if not forecasts:
        raise WeatherForecastNotFoundError("weather forecast not found")

    selected = min(forecasts, key=lambda item: abs(item.forecast_at - target))
    if abs(selected.forecast_at - target) > timedelta(hours=1):
        raise WeatherForecastNotFoundError("weather forecast not found near requested time")
    return ForecastWeatherResponse(
        latitude=latitude,
        longitude=longitude,
        forecast_at=selected.forecast_at,
        temperature=selected.temperature,
        humidity=selected.humidity,
        apparent_temperature=selected.apparent_temperature,
    )


async def _get_short_term_forecasts(
    latitude: float,
    longitude: float,
    *,
    now: datetime,
) -> list[WeatherValue]:
    base_at = _latest_village_forecast_base(now)
    grid_x, grid_y = latitude_longitude_to_grid(latitude, longitude)
    items = await _request_kma(
        "getVilageFcst",
        base_at=base_at,
        grid_x=grid_x,
        grid_y=grid_y,
    )
    grouped: dict[datetime, dict[str, float]] = defaultdict(dict)
    for item in items:
        category = str(item["category"])
        if category not in {"TMP", "REH", "WSD"}:
            continue
        forecast_at = _item_datetime(item, "fcstDate", "fcstTime")
        grouped[forecast_at][category] = float(item["fcstValue"])

    forecasts: list[WeatherValue] = []
    for forecast_at, values in sorted(grouped.items()):
        if "TMP" not in values or "REH" not in values:
            continue
        forecasts.append(
            WeatherValue(
                forecast_at=forecast_at,
                temperature=values["TMP"],
                humidity=values["REH"],
                apparent_temperature=calculate_apparent_temperature(
                    values["TMP"],
                    values["REH"],
                    forecast_at,
                    values.get("WSD"),
                ),
            )
        )
    return forecasts


async def _request_kma(
    operation: str,
    *,
    base_at: datetime,
    grid_x: int,
    grid_y: int,
) -> list[dict[str, Any]]:
    if not settings.kma_api_key:
        raise WeatherConfigurationError("KMA_API_KEY is not configured")

    params = {
        "serviceKey": unquote(settings.kma_api_key),
        "pageNo": 1,
        "numOfRows": 1000,
        "dataType": "JSON",
        "base_date": base_at.strftime("%Y%m%d"),
        "base_time": base_at.strftime("%H%M"),
        "nx": grid_x,
        "ny": grid_y,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.kma_api_base_url}/{operation}",
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise WeatherProviderError("KMA API request failed") from exc

    try:
        api_response = payload["response"]
        header = api_response["header"]
        if str(header["resultCode"]) != "00":
            raise WeatherProviderError(str(header.get("resultMsg", "KMA API error")))
        items = api_response["body"]["items"]["item"]
    except (KeyError, TypeError) as exc:
        raise WeatherProviderError("unexpected KMA API response") from exc
    return list(items)


def _latest_ultra_nowcast_base(now: datetime) -> datetime:
    base = now.replace(minute=0, second=0, microsecond=0)
    if now.minute < 45:
        base -= timedelta(hours=1)
    return base


def _latest_village_forecast_base(now: datetime) -> datetime:
    release_hours = (2, 5, 8, 11, 14, 17, 20, 23)
    for hour in reversed(release_hours):
        candidate = datetime.combine(now.date(), time(hour, 10), tzinfo=SEOUL_TZ)
        if now >= candidate:
            return candidate.replace(minute=0)
    previous_day = now.date() - timedelta(days=1)
    return datetime.combine(previous_day, time(23), tzinfo=SEOUL_TZ)


def _item_datetime(
    item: dict[str, Any],
    date_field: str,
    time_field: str,
) -> datetime:
    return datetime.strptime(
        f"{item[date_field]}{str(item[time_field]).zfill(4)}",
        "%Y%m%d%H%M",
    ).replace(tzinfo=SEOUL_TZ)


def _seoul_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(SEOUL_TZ)
    return _as_seoul_datetime(now)


def _as_seoul_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=SEOUL_TZ)
    return value.astimezone(SEOUL_TZ)

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.config import settings
from app.schemas.asos import AsosHourlyObservation, AsosHourlyResponse
from app.services.external_api import ExternalApiError, request_public_data_json

SEOUL_TZ = ZoneInfo("Asia/Seoul")
HOURLY_SOLAR_RADIATION_TO_WATTS = 1_000_000 / 3_600


class AsosConfigurationError(Exception):
    """ASOS API 설정이 없습니다."""


class AsosProviderError(Exception):
    """ASOS API 요청 또는 응답 처리에 실패했습니다."""


class AsosDataNotFoundError(Exception):
    """요청한 ASOS 관측자료가 없습니다."""


async def get_asos_hourly(
    station_id: int,
    start_at: datetime,
    end_at: datetime,
) -> AsosHourlyResponse:
    if station_id <= 0:
        raise ValueError("station_id must be positive")
    start = _as_seoul_datetime(start_at)
    end = _as_seoul_datetime(end_at)
    if end < start:
        raise ValueError("end_at must be greater than or equal to start_at")
    if end - start > timedelta(days=31):
        raise ValueError("ASOS hourly query cannot exceed 31 days")

    api_key = settings.kma_asos_api_key or settings.kma_api_key
    if not api_key:
        raise AsosConfigurationError("KMA_ASOS_API_KEY or KMA_API_KEY is not configured")

    try:
        payload = await request_public_data_json(
            f"{settings.kma_asos_api_base_url}/getWthrDataList",
            api_key,
            {
                "pageNo": 1,
                # The ASOS gateway rejects exactly 1,000 despite documenting a
                # 1,000-row ceiling, so use the largest accepted value.
                "numOfRows": 999,
                "dataType": "JSON",
                "dataCd": "ASOS",
                "dateCd": "HR",
                "startDt": start.strftime("%Y%m%d"),
                "startHh": start.strftime("%H"),
                "endDt": end.strftime("%Y%m%d"),
                "endHh": end.strftime("%H"),
                "stnIds": station_id,
            },
        )
    except ExternalApiError as exc:
        raise AsosProviderError("ASOS API request failed") from exc

    items = _extract_items(payload)
    if not items:
        raise AsosDataNotFoundError("ASOS observations not found")
    observations = [_parse_observation(item) for item in items]
    observations.sort(key=lambda item: item.observed_at)
    station_name = observations[0].station_name
    return AsosHourlyResponse(
        station_id=station_id,
        station_name=station_name,
        start_at=start,
        end_at=end,
        observations=observations,
    )


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        response = payload["response"]
        header = response["header"]
        if str(header["resultCode"]) != "00":
            raise AsosProviderError(str(header.get("resultMsg", "ASOS API error")))
        items = response["body"]["items"]["item"]
    except AsosProviderError:
        raise
    except (KeyError, TypeError) as exc:
        raise AsosProviderError("unexpected ASOS API response") from exc
    if isinstance(items, dict):
        return [items]
    if not isinstance(items, list):
        raise AsosProviderError("unexpected ASOS observation list")
    return items


def _parse_observation(item: dict[str, Any]) -> AsosHourlyObservation:
    try:
        station_id = int(item["stnId"])
        station_name = str(item["stnNm"])
        observed_at = _parse_observed_at(str(item["tm"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise AsosProviderError("ASOS observation has invalid identity fields") from exc

    hourly_solar = _number(item.get("icsr"))
    solar_radiation = (
        hourly_solar * HOURLY_SOLAR_RADIATION_TO_WATTS
        if hourly_solar is not None
        else None
    )
    return AsosHourlyObservation(
        station_id=station_id,
        station_name=station_name,
        observed_at=observed_at,
        temperature=_number(item.get("ta")),
        humidity=_number(item.get("hm")),
        wind_speed=_number(item.get("ws")),
        solar_radiation=solar_radiation,
        surface_pressure=_number(item.get("pa")),
        sea_level_pressure=_number(item.get("ps")),
        dew_point=_number(item.get("td")),
    )


def _parse_observed_at(value: str) -> datetime:
    for date_format in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H"):
        try:
            return datetime.strptime(value, date_format).replace(tzinfo=SEOUL_TZ)
        except ValueError:
            continue
    raise ValueError(f"unsupported ASOS timestamp: {value}")


def _number(value: Any) -> float | None:
    if value is None or str(value).strip() in {"", "-", "null", "None"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise AsosProviderError(f"ASOS numeric value is invalid: {value!r}") from exc


def _as_seoul_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=SEOUL_TZ)
    return value.astimezone(SEOUL_TZ)

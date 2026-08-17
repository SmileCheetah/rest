import asyncio
from datetime import datetime, time, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from app.config import settings
from app.schemas.living_index import LivingIndexResponse, LivingIndexValue
from app.services.external_api import ExternalApiError, request_public_data_json

SEOUL_TZ = ZoneInfo("Asia/Seoul")
SEOUL_AREA_NO = "1100000000"
IndexKind = Literal["uv", "air"]


class LivingIndexConfigurationError(Exception):
    """생활기상지수 API 설정이 없습니다."""


class LivingIndexProviderError(Exception):
    """생활기상지수 API 호출 또는 응답 처리에 실패했습니다."""


async def get_living_weather_index(
    area_no: str = SEOUL_AREA_NO,
    *,
    now: datetime | None = None,
) -> LivingIndexResponse:
    current = _seoul_now(now)
    base_at = _latest_living_index_base(current)
    ultraviolet_item, air_item = await asyncio.gather(
        _request_index("getUVIdxV5", area_no, base_at),
        _request_index("getAirDiffusionIdxV5", area_no, base_at),
    )
    published_at = _parse_datetime(ultraviolet_item.get("date")) or base_at
    return LivingIndexResponse(
        area_no=area_no,
        published_at=published_at,
        ultraviolet=_select_index_value(ultraviolet_item, current, "uv"),
        air_diffusion=_select_index_value(air_item, current, "air"),
    )


async def _request_index(
    operation: str,
    area_no: str,
    base_at: datetime,
) -> dict[str, Any]:
    if not settings.kma_living_index_api_key:
        raise LivingIndexConfigurationError("KMA_LIVING_INDEX_API_KEY is not configured")
    try:
        payload = await request_public_data_json(
            f"{settings.kma_living_index_api_base_url}/{operation}",
            settings.kma_living_index_api_key,
            {
                "pageNo": 1,
                "numOfRows": 10,
                "dataType": "JSON",
                "areaNo": area_no,
                "time": base_at.strftime("%Y%m%d%H"),
            },
            api_key_name="ServiceKey",
        )
    except ExternalApiError as exc:
        raise LivingIndexProviderError("KMA living index API request failed") from exc
    try:
        response = payload["response"]
        header = response["header"]
        if str(header["resultCode"]) not in {"00", "0"}:
            raise LivingIndexProviderError(str(header.get("resultMsg", "KMA living index API error")))
        raw_item = response["body"]["items"]["item"]
    except (KeyError, TypeError) as exc:
        raise LivingIndexProviderError("unexpected KMA living index API response") from exc
    if isinstance(raw_item, list):
        if not raw_item:
            raise LivingIndexProviderError("KMA living index data is empty")
        return raw_item[0]
    if isinstance(raw_item, dict):
        return raw_item
    raise LivingIndexProviderError("KMA living index data is empty")


def _select_index_value(
    item: dict[str, Any],
    current: datetime,
    kind: IndexKind,
) -> LivingIndexValue:
    published_at = _parse_datetime(item.get("date"))
    if published_at is None:
        raise LivingIndexProviderError("living index publication time is missing")
    candidates: list[tuple[datetime, float]] = []
    for key, raw_value in item.items():
        if not key.startswith("h") or not key[1:].isdigit():
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        candidates.append((published_at + timedelta(hours=int(key[1:])), value))
    if not candidates:
        raise LivingIndexProviderError("living index predictions are missing")
    forecast_at, value = min(candidates, key=lambda candidate: abs(candidate[0] - current))
    label = ultraviolet_label(value) if kind == "uv" else air_diffusion_label(value)
    return LivingIndexValue(value=value, label=label, forecast_at=forecast_at)


def ultraviolet_label(value: float) -> str:
    if value < 3:
        return "낮음"
    if value <= 5:
        return "보통"
    if value <= 7:
        return "높음"
    if value <= 10:
        return "매우 높음"
    return "위험"


def air_diffusion_label(value: float) -> str:
    if value <= 25:
        return "낮음"
    if value <= 50:
        return "보통"
    if value <= 75:
        return "높음"
    return "매우 높음"


def _latest_living_index_base(now: datetime) -> datetime:
    evening = datetime.combine(now.date(), time(18, 10), tzinfo=SEOUL_TZ)
    morning = datetime.combine(now.date(), time(6, 10), tzinfo=SEOUL_TZ)
    if now >= evening:
        return evening.replace(minute=0)
    if now >= morning:
        return morning.replace(minute=0)
    return datetime.combine(now.date() - timedelta(days=1), time(18), tzinfo=SEOUL_TZ)


def _parse_datetime(value: object) -> datetime | None:
    digits = "".join(character for character in str(value) if character.isdigit())
    if len(digits) < 10:
        return None
    try:
        return datetime.strptime(digits[:10], "%Y%m%d%H").replace(tzinfo=SEOUL_TZ)
    except ValueError:
        return None


def _seoul_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(SEOUL_TZ)
    if now.tzinfo is None:
        return now.replace(tzinfo=SEOUL_TZ)
    return now.astimezone(SEOUL_TZ)

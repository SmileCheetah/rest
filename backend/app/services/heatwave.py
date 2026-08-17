from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.config import settings
from app.schemas.heatwave import (
    HeatwaveCategoryForecast,
    HeatwaveCurrentResponse,
    HeatwaveLevel,
)
from app.services.external_api import ExternalApiError, request_public_data_json

SEOUL_TZ = ZoneInfo("Asia/Seoul")
SEOUL_IMPACT_REGION_ID = "11B10101"
SEOUL_REGION_NAME = "서울"
LEVEL_ORDER: dict[HeatwaveLevel, int] = {
    "NONE": 0,
    "INTEREST": 1,
    "CAUTION": 2,
    "WARNING": 3,
    "DANGER": 4,
}


class HeatwaveConfigurationError(Exception):
    """영향예보 API 설정이 없습니다."""


class HeatwaveProviderError(Exception):
    """영향예보 API 호출 또는 응답 처리에 실패했습니다."""


async def get_current_heatwave_impact(
    *,
    now: datetime | None = None,
) -> HeatwaveCurrentResponse:
    current = _seoul_now(now)
    announced_date = current.date() if current.time() >= time(12) else current.date() - timedelta(days=1)
    announced_at = datetime.combine(announced_date, time(11, 30), tzinfo=SEOUL_TZ)
    items = await _request_heatwave_impact(announced_date)
    forecasts = _to_category_forecasts(items, current.date())
    if not forecasts:
        return HeatwaveCurrentResponse(
            region_id=SEOUL_IMPACT_REGION_ID,
            region_name=SEOUL_REGION_NAME,
            announced_at=announced_at,
            effective_date=None,
            level="NONE",
            label="발표 없음",
            has_announcement=False,
            forecasts=[],
        )

    overall = max(forecasts, key=lambda item: LEVEL_ORDER[item.level])
    return HeatwaveCurrentResponse(
        region_id=SEOUL_IMPACT_REGION_ID,
        region_name=str(items[0].get("regName") or SEOUL_REGION_NAME),
        announced_at=announced_at,
        effective_date=overall.effective_date,
        level=overall.level,
        label=overall.label,
        has_announcement=True,
        forecasts=forecasts,
    )


async def _request_heatwave_impact(announced_date: date) -> list[dict[str, Any]]:
    if not settings.kma_impact_api_key:
        raise HeatwaveConfigurationError("KMA_IMPACT_API_KEY is not configured")
    try:
        payload = await request_public_data_json(
            f"{settings.kma_impact_api_base_url}/getHWImpactValueV2",
            settings.kma_impact_api_key,
            {
                "pageNo": 1,
                "numOfRows": 100,
                "dataType": "JSON",
                "regId": SEOUL_IMPACT_REGION_ID,
                "tm": announced_date.strftime("%Y%m%d"),
                "efSn": 3,
            },
        )
    except ExternalApiError as exc:
        raise HeatwaveProviderError("KMA impact API request failed") from exc
    return _extract_items(payload)


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        response = payload["response"]
        header = response["header"]
        result_code = str(header["resultCode"])
        if result_code == "03":
            return []
        if result_code != "00":
            raise HeatwaveProviderError(str(header.get("resultMsg", "KMA impact API error")))
        raw_items = response["body"].get("items", {}).get("item", [])
    except (KeyError, TypeError) as exc:
        raise HeatwaveProviderError("unexpected KMA impact API response") from exc
    if isinstance(raw_items, dict):
        return [raw_items]
    if isinstance(raw_items, list):
        return raw_items
    return []


def _to_category_forecasts(
    items: list[dict[str, Any]],
    today: date,
) -> list[HeatwaveCategoryForecast]:
    forecasts: list[HeatwaveCategoryForecast] = []
    for item in items:
        if str(item.get("regId")) != SEOUL_IMPACT_REGION_ID:
            continue
        effective_date = _parse_date(item.get("tmEf"))
        if effective_date is None or effective_date < today:
            continue
        level, label = normalize_heatwave_level(str(item.get("value", "")))
        forecasts.append(
            HeatwaveCategoryForecast(
                category=str(item.get("clsfc") or "기타"),
                level=level,
                label=label,
                effective_date=effective_date,
            )
        )
    return forecasts


def normalize_heatwave_level(value: str) -> tuple[HeatwaveLevel, str]:
    normalized = value.strip()
    mapping: dict[str, tuple[HeatwaveLevel, str]] = {
        "관심": ("INTEREST", "관심"),
        "주의": ("CAUTION", "주의"),
        "경고": ("WARNING", "경고"),
        "위험": ("DANGER", "위험"),
        "심각": ("DANGER", "위험"),
    }
    return mapping.get(normalized, ("NONE", "발표 없음"))


def _parse_date(value: object) -> date | None:
    digits = "".join(character for character in str(value) if character.isdigit())
    if len(digits) < 8:
        return None
    try:
        return datetime.strptime(digits[:8], "%Y%m%d").date()
    except ValueError:
        return None


def _seoul_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(SEOUL_TZ)
    if now.tzinfo is None:
        return now.replace(tzinfo=SEOUL_TZ)
    return now.astimezone(SEOUL_TZ)

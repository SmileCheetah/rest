from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

SEOUL_TIMEZONE = ZoneInfo("Asia/Seoul")


def seoul_today() -> date:
    """서비스 기준 시간대인 Asia/Seoul의 오늘 날짜를 반환합니다."""
    return datetime.now(SEOUL_TIMEZONE).date()


def utc_naive_to_seoul(value: datetime | None) -> datetime | None:
    """DB의 UTC naive datetime을 Asia/Seoul 시간으로 변환합니다."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(SEOUL_TIMEZONE)

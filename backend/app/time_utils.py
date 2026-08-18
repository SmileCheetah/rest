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


def to_utc_naive(value: datetime) -> datetime:
    """서울 기준 datetime을 DB 저장용 UTC naive datetime으로 변환합니다."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=SEOUL_TIMEZONE)
    return value.astimezone(UTC).replace(tzinfo=None)


def to_utc_aware(value: datetime) -> datetime:
    """시간대 유무와 무관하게 비교 가능한 UTC aware datetime을 반환합니다.

    API로 받은 시간대 없는 값은 서비스 기준 시간대(서울)로 해석합니다.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=SEOUL_TIMEZONE)
    return value.astimezone(UTC)

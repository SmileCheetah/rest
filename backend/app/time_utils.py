from datetime import date, datetime
from zoneinfo import ZoneInfo

SEOUL_TIMEZONE = ZoneInfo("Asia/Seoul")


def seoul_today() -> date:
    """서비스 기준 시간대인 Asia/Seoul의 오늘 날짜를 반환합니다."""
    return datetime.now(SEOUL_TIMEZONE).date()


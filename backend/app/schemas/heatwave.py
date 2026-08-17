from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

HeatwaveLevel = Literal["NONE", "INTEREST", "CAUTION", "WARNING", "DANGER"]


class HeatwaveCategoryForecast(BaseModel):
    """분야별 폭염 영향예보입니다."""

    model_config = ConfigDict(populate_by_name=True)

    category: str
    level: HeatwaveLevel
    label: str
    effective_date: date = Field(serialization_alias="effectiveDate")


class HeatwaveCurrentResponse(BaseModel):
    """서울 지역의 공식 폭염 영향예보입니다."""

    model_config = ConfigDict(populate_by_name=True)

    region_id: str = Field(serialization_alias="regionId")
    region_name: str = Field(serialization_alias="regionName")
    announced_at: datetime = Field(serialization_alias="announcedAt")
    effective_date: date | None = Field(serialization_alias="effectiveDate")
    level: HeatwaveLevel
    label: str
    has_announcement: bool = Field(serialization_alias="hasAnnouncement")
    forecasts: list[HeatwaveCategoryForecast]
    source: str = "KMA"

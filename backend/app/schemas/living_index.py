from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LivingIndexValue(BaseModel):
    """특정 시각의 생활기상지수입니다."""

    model_config = ConfigDict(populate_by_name=True)

    value: float
    label: str
    forecast_at: datetime = Field(serialization_alias="forecastAt")


class LivingIndexResponse(BaseModel):
    """자외선지수와 대기정체지수 응답입니다."""

    model_config = ConfigDict(populate_by_name=True)

    area_no: str = Field(serialization_alias="areaNo")
    published_at: datetime = Field(serialization_alias="publishedAt")
    ultraviolet: LivingIndexValue
    air_diffusion: LivingIndexValue = Field(serialization_alias="airDiffusion")
    source: str = "KMA"

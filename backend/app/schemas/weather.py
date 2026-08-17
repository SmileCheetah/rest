from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class WeatherValue(BaseModel):
    """특정 시각의 기상정보입니다."""

    model_config = ConfigDict(populate_by_name=True)

    forecast_at: datetime = Field(serialization_alias="forecastAt")
    temperature: float
    humidity: float
    apparent_temperature: float = Field(serialization_alias="apparentTemperature")


class CurrentWeatherResponse(BaseModel):
    """현재 위치의 초단기실황 응답입니다."""

    model_config = ConfigDict(populate_by_name=True)

    latitude: float
    longitude: float
    grid_x: int = Field(serialization_alias="gridX")
    grid_y: int = Field(serialization_alias="gridY")
    observed_at: datetime = Field(serialization_alias="observedAt")
    temperature: float
    humidity: float
    apparent_temperature: float = Field(serialization_alias="apparentTemperature")
    source: str = "KMA"


class HourlyWeatherResponse(BaseModel):
    """선택한 날짜의 시간대별 단기예보 응답입니다."""

    model_config = ConfigDict(populate_by_name=True)

    latitude: float
    longitude: float
    forecast_date: date = Field(serialization_alias="forecastDate")
    forecasts: list[WeatherValue]
    source: str = "KMA"


class ForecastWeatherResponse(WeatherValue):
    """방문 예정 시각과 가장 가까운 단기예보 응답입니다."""

    latitude: float
    longitude: float
    source: str = "KMA"

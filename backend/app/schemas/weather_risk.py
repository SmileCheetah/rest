from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WeatherRiskBasis = Literal["WBGT", "APPARENT_TEMPERATURE"]
WeatherRiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


class WeatherRiskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    station_id: int = Field(default=108, ge=1, alias="stationId")
    observed_at: datetime = Field(..., alias="observedAt")
    temperature: float | None = None
    humidity: float | None = Field(default=None, ge=0, le=100)
    wind_speed: float | None = Field(default=None, ge=0, alias="windSpeed")
    solar_radiation: float | None = Field(default=None, ge=0, alias="solarRadiation")
    surface_pressure: float | None = Field(
        default=None,
        ge=800,
        le=1_100,
        alias="surfacePressure",
    )
    wbgt: float | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class WeatherRiskReferencePoint(BaseModel):
    value: float
    score: int


class WeatherRiskResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    weather_risk_score: int = Field(alias="weatherRiskScore")
    weather_risk_level: WeatherRiskLevel = Field(alias="weatherRiskLevel")
    weather_risk_level_ko: str = Field(alias="weatherRiskLevelKo")
    basis: WeatherRiskBasis
    input_value: float = Field(alias="inputValue")
    work_intensity: str = Field(alias="workIntensity")
    weather_source: Literal["KMA_ASOS", "REQUEST_FALLBACK"] = Field(
        alias="weatherSource"
    )
    reference: dict[str, WeatherRiskReferencePoint] | None = None
    explanation: str

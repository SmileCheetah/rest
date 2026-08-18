from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AsosHourlyObservation(BaseModel):
    """기상청 ASOS 한 지점의 정시 관측값입니다."""

    model_config = ConfigDict(populate_by_name=True)

    station_id: int = Field(serialization_alias="stationId")
    station_name: str = Field(serialization_alias="stationName")
    observed_at: datetime = Field(serialization_alias="observedAt")
    temperature: float | None = None
    humidity: float | None = Field(default=None, ge=0, le=100)
    wind_speed: float | None = Field(default=None, ge=0, serialization_alias="windSpeed")
    solar_radiation: float | None = Field(
        default=None,
        ge=0,
        serialization_alias="solarRadiation",
        description="ASOS icsr converted from MJ/m2 per hour to W/m2",
    )
    surface_pressure: float | None = Field(
        default=None,
        ge=800,
        le=1_100,
        serialization_alias="surfacePressure",
    )
    sea_level_pressure: float | None = Field(
        default=None,
        ge=800,
        le=1_100,
        serialization_alias="seaLevelPressure",
    )
    dew_point: float | None = Field(default=None, serialization_alias="dewPoint")


class AsosHourlyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    station_id: int = Field(serialization_alias="stationId")
    station_name: str = Field(serialization_alias="stationName")
    start_at: datetime = Field(serialization_alias="startAt")
    end_at: datetime = Field(serialization_alias="endAt")
    observations: list[AsosHourlyObservation]
    source: str = "KMA_ASOS"

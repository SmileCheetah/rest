from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.enums import RouteType
from app.schemas.weather import ForecastWeatherResponse
from app.time_utils import utc_naive_to_seoul


class Coordinate(BaseModel):
    """WGS84 위·경도입니다."""

    latitude: float = Field(ge=33.0, le=39.0)
    longitude: float = Field(ge=124.0, le=132.0)
    name: str | None = Field(default=None, max_length=100)


class RoutePathPoint(BaseModel):
    latitude: float
    longitude: float


class NormalRouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    departureTime: datetime


class NormalRouteResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    origin: Coordinate
    destination: Coordinate
    distance_meters: int = Field(serialization_alias="distanceMeters")
    walking_minutes: int = Field(serialization_alias="walkingMinutes")
    estimated_arrival_time: datetime = Field(
        serialization_alias="estimatedArrivalTime"
    )
    path: list[RoutePathPoint]
    source: str = "TMAP"


class RouteSegmentCreateRequest(NormalRouteRequest):
    workSessionId: int = Field(gt=0)
    scheduleId: int = Field(gt=0)


class RouteSegmentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    route_segment_id: int = Field(serialization_alias="routeSegmentId")
    route_option_id: int = Field(serialization_alias="routeOptionId")
    work_session_id: int = Field(serialization_alias="workSessionId")
    schedule_id: int = Field(serialization_alias="scheduleId")
    route_type: RouteType = Field(serialization_alias="routeType")
    origin: Coordinate
    destination: Coordinate
    departure_time: datetime | None = Field(serialization_alias="departureTime")
    distance_meters: int = Field(serialization_alias="distanceMeters")
    walking_minutes: int = Field(serialization_alias="walkingMinutes")
    estimated_arrival_time: datetime | None = Field(
        serialization_alias="estimatedArrivalTime"
    )
    path: list[RoutePathPoint]
    weather: ForecastWeatherResponse | None = None

    @field_serializer(
        "departure_time",
        "estimated_arrival_time",
        when_used="json",
    )
    def serialize_db_datetime(self, value: datetime | None) -> datetime | None:
        return utc_naive_to_seoul(value)

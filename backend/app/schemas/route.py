from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.enums import RouteType
from app.schemas.cooling_spot import CoolingSpotResponse
from app.schemas.risk_analysis import RiskEvaluateResponse
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


class SafeRouteRequest(BaseModel):
    """일반 이동구간을 기준으로 쿨링스팟 경유 안전경로를 생성합니다."""

    routeSegmentId: int = Field(gt=0)
    coolingSpotId: int | None = Field(default=None, gt=0)
    plannedRestMinutes: int = Field(default=10, ge=5, le=60)
    maxAdditionalMinutes: int = Field(default=5, ge=0, le=20)


class SafeRouteResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    route_segment_id: int = Field(serialization_alias="routeSegmentId")
    route_option_id: int = Field(serialization_alias="routeOptionId")
    route_type: RouteType = Field(serialization_alias="routeType")
    cooling_spot: CoolingSpotResponse = Field(serialization_alias="coolingSpot")
    distance_meters: int = Field(serialization_alias="distanceMeters")
    walking_minutes: int = Field(serialization_alias="walkingMinutes")
    total_travel_minutes: int = Field(serialization_alias="totalTravelMinutes")
    additional_minutes: int = Field(serialization_alias="additionalMinutes")
    planned_rest_minutes: int = Field(serialization_alias="plannedRestMinutes")
    estimated_arrival_time: datetime = Field(serialization_alias="estimatedArrivalTime")
    path: list[RoutePathPoint]


class RouteOptionSelectionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    route_option_id: int = Field(serialization_alias="routeOptionId")
    selected: bool


class RouteRecommendationRequest(BaseModel):
    """위험 판단부터 쿨링스팟 경유 안전경로 추천까지 한 번에 실행합니다."""

    routeSegmentId: int = Field(gt=0)
    currentContinuousExposureMinutes: int = Field(default=0, ge=0, le=600)
    plannedRestMinutes: int = Field(default=10, ge=5, le=60)
    maxAdditionalMinutes: int = Field(default=5, ge=0, le=20)


class RouteRecommendationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    risk: RiskEvaluateResponse
    normal_route: RouteSegmentResponse = Field(serialization_alias="normalRoute")
    safe_route: SafeRouteResponse | None = Field(default=None, serialization_alias="safeRoute")
    shelter_recommendation_message: str | None = Field(
        default=None,
        serialization_alias="shelterRecommendationMessage",
    )

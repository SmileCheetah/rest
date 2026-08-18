from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.enums import WorkSessionStatus
from app.time_utils import utc_naive_to_seoul


class WorkSessionStartRequest(BaseModel):
    """업무 시작 요청입니다."""

    workDate: date


class WorkSessionResponse(BaseModel):
    """업무 세션 상태와 방문 진행 현황 응답입니다."""

    model_config = ConfigDict(populate_by_name=True)

    work_session_id: int = Field(serialization_alias="workSessionId")
    work_date: date = Field(serialization_alias="workDate")
    status: WorkSessionStatus
    started_at: datetime | None = Field(serialization_alias="startedAt")
    completed_at: datetime | None = Field(serialization_alias="completedAt")
    completed_visit_count: int = Field(serialization_alias="completedVisitCount")
    total_visit_count: int = Field(serialization_alias="totalVisitCount")
    total_exposure_minutes: int = Field(serialization_alias="totalExposureMinutes")
    max_continuous_exposure_minutes: int = Field(
        serialization_alias="maxContinuousExposureMinutes"
    )
    total_rest_minutes: int = Field(serialization_alias="totalRestMinutes")
    rest_count: int = Field(serialization_alias="restCount")
    heat_exposure_reduction_minutes: int = Field(
        serialization_alias="heatExposureReductionMinutes"
    )
    used_cooling_spot_names: list[str] = Field(
        default_factory=list,
        serialization_alias="usedCoolingSpotNames",
    )

    @field_serializer("started_at", "completed_at", when_used="json")
    def serialize_datetime(self, value: datetime | None) -> datetime | None:
        return utc_naive_to_seoul(value)

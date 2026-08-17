from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from app.models.enums import ScheduleStatus
from app.schemas.visit_target import VisitTargetResponse
from app.time_utils import utc_naive_to_seoul


class ScheduleCreateRequest(BaseModel):
    """방문 일정 생성 요청입니다."""

    visitTargetId: int = Field(gt=0)
    scheduleDate: date
    scheduledTime: time
    visitOrder: int = Field(gt=0)
    plannedVisitMinutes: int | None = Field(default=None, ge=0)


class ScheduleUpdateRequest(BaseModel):
    """방문 일정 부분 수정 요청입니다."""

    scheduledTime: time | None = None
    visitOrder: int | None = Field(default=None, gt=0)
    plannedVisitMinutes: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "ScheduleUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self


class ScheduleResponse(BaseModel):
    """방문 일정 조회 응답입니다."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(serialization_alias="scheduleId")
    work_session_id: int = Field(serialization_alias="workSessionId")
    scheduled_time: time = Field(serialization_alias="scheduledTime")
    visit_order: int = Field(serialization_alias="visitOrder")
    status: ScheduleStatus
    planned_visit_minutes: int | None = Field(
        serialization_alias="plannedVisitMinutes"
    )
    completed_at: datetime | None = Field(serialization_alias="completedAt")
    visit_target: VisitTargetResponse = Field(serialization_alias="visitTarget")

    @field_serializer("completed_at", when_used="json")
    def serialize_completed_at(self, value: datetime | None) -> datetime | None:
        return utc_naive_to_seoul(value)


class NextScheduleResponse(BaseModel):
    """다음 방문 일정과 전체 완료 여부 응답입니다."""

    model_config = ConfigDict(populate_by_name=True)

    work_session_id: int = Field(serialization_alias="workSessionId")
    work_completed: bool = Field(serialization_alias="workCompleted")
    next_schedule: ScheduleResponse | None = Field(serialization_alias="nextSchedule")

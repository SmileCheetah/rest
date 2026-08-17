from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ScheduleStatus
from app.schemas.visit_target import VisitTargetResponse


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


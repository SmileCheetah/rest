from typing import Literal

from pydantic import BaseModel, Field


class ExposureState(BaseModel):
    continuous_exposure_minutes: int = Field(0, ge=0)
    daily_exposure_minutes: int = Field(0, ge=0)
    daily_rest_minutes: int = Field(0, ge=0)
    current_rest_minutes: int = Field(0, ge=0)


def update_exposure(
    state: ExposureState,
    activity_type: Literal["MOVING", "VISITING", "RESTING", "IDLE"],
    duration_minutes: int,
    is_outdoor: bool,
) -> tuple[ExposureState, bool, list[str]]:
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be greater than 0")
    next_state = state.model_copy(deep=True)
    reasons: list[str] = []
    rest_completed = False
    if activity_type == "RESTING":
        previous = next_state.current_rest_minutes
        next_state.current_rest_minutes += duration_minutes
        next_state.daily_rest_minutes += duration_minutes
        rest_completed = previous < 20 <= next_state.current_rest_minutes
        if rest_completed:
            next_state.continuous_exposure_minutes = 0
        reasons.append(f"{duration_minutes}분 휴식을 반영했습니다.")
    elif is_outdoor:
        next_state.continuous_exposure_minutes += duration_minutes
        next_state.daily_exposure_minutes += duration_minutes
        next_state.current_rest_minutes = 0
        reasons.append(f"{duration_minutes}분 야외활동을 반영했습니다.")
    else:
        next_state.current_rest_minutes = 0
        reasons.append("실내 활동으로 야외 노출에 반영하지 않았습니다.")
    return next_state, rest_completed, reasons

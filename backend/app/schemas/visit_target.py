from pydantic import BaseModel, ConfigDict, Field


class VisitTargetResponse(BaseModel):
    """방문대상자 조회 응답입니다."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(serialization_alias="visitTargetId")
    name: str
    address: str
    latitude: float
    longitude: float


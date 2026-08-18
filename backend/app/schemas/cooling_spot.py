from datetime import time

from pydantic import BaseModel, ConfigDict, Field


class CoolingSpotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    address: str
    latitude: float
    longitude: float
    open_time: time | None = Field(serialization_alias="openTime")
    close_time: time | None = Field(serialization_alias="closeTime")
    facilities: dict | None
    source: str | None

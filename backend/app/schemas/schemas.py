from datetime import datetime
from pydantic import BaseModel, Field


class BuildingOut(BaseModel):
    id: int
    name: str
    floors: int
    model_config = {"from_attributes": True}


class CarOut(BaseModel):
    id: int
    building_id: int
    label: str
    floor: int
    direction: str
    load: int
    capacity: int
    accessible: bool
    model_config = {"from_attributes": True}


class CarUpdate(BaseModel):
    accessible: bool


class CallOut(BaseModel):
    id: int
    building_id: int
    floor: int
    direction: str
    passengers: int
    needs_accessible: bool
    status: str
    assigned_car_id: int | None
    score: str
    created_at: datetime
    model_config = {"from_attributes": True}


class CallCreate(BaseModel):
    building_id: int
    floor: int = Field(ge=1)
    direction: str
    passengers: int = Field(ge=1, le=8)
    needs_accessible: bool = False


class DispatchRequest(BaseModel):
    call_id: int


class DispatchResult(CallOut):
    detail: str


class LogOut(BaseModel):
    id: int
    call_id: int
    car_id: int | None
    detail: str
    created_at: datetime
    model_config = {"from_attributes": True}


class CongestionFloor(BaseModel):
    floor: int
    passengers: int

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import UnitEnum


class CropBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    local_name: Optional[str] = None
    category: str = Field(..., description="e.g. CEREALS, PULSES, VEGETABLES, FRUITS, OILSEEDS")
    variety: Optional[str] = None
    default_unit: UnitEnum = Field(default=UnitEnum.QUINTAL)
    is_active: bool = True


class CropCreate(CropBase):
    pass


class CropUpdate(BaseModel):
    name: Optional[str] = None
    local_name: Optional[str] = None
    category: Optional[str] = None
    variety: Optional[str] = None
    default_unit: Optional[UnitEnum] = None
    is_active: Optional[bool] = None


class CropResponse(CropBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

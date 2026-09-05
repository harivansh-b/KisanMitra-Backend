from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import QualityGrade, RequirementStatus, UnitEnum
from app.schemas.crop import CropResponse


class BuyerRequirementBase(BaseModel):
    crop_id: str
    variety: Optional[str] = None
    required_quantity: float = Field(..., gt=0)
    unit: UnitEnum = Field(default=UnitEnum.QUINTAL)
    quality_grade: Optional[QualityGrade] = None
    target_price: float = Field(..., gt=0, description="Target purchase price per unit in INR")
    delivery_location: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    required_from: Optional[datetime] = None
    required_until: Optional[datetime] = None
    description: Optional[str] = None


class BuyerRequirementCreate(BuyerRequirementBase):
    pass


class BuyerRequirementUpdate(BaseModel):
    crop_id: Optional[str] = None
    variety: Optional[str] = None
    required_quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[UnitEnum] = None
    quality_grade: Optional[QualityGrade] = None
    target_price: Optional[float] = Field(None, gt=0)
    delivery_location: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    required_from: Optional[datetime] = None
    required_until: Optional[datetime] = None
    description: Optional[str] = None
    status: Optional[RequirementStatus] = None


class BuyerRequirementResponse(BuyerRequirementBase):
    id: str
    buyer_id: str
    status: RequirementStatus
    created_at: datetime
    updated_at: datetime
    crop: Optional[CropResponse] = None

    model_config = ConfigDict(from_attributes=True)


class BuyerRequirementFilter(BaseModel):
    crop_id: Optional[str] = None
    category: Optional[str] = None
    variety: Optional[str] = None
    quality_grade: Optional[QualityGrade] = None
    status: Optional[RequirementStatus] = RequirementStatus.ACTIVE
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    # Spatial filter
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = Field(None, gt=0, description="Radius in kilometers")

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import ListingStatus, QualityGrade, SellerType, UnitEnum
from app.schemas.crop import CropResponse


class ProduceListingBase(BaseModel):
    crop_id: str
    variety: Optional[str] = None
    quantity: float = Field(..., gt=0)
    unit: UnitEnum = Field(default=UnitEnum.QUINTAL)
    quality_grade: QualityGrade = Field(default=QualityGrade.GRADE_A)
    harvest_date: Optional[date] = None
    expected_price: float = Field(..., gt=0, description="Price per unit in INR")
    min_price: Optional[float] = Field(None, gt=0, description="Minimum acceptable price")
    location_name: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    description: Optional[str] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class ProduceListingCreate(ProduceListingBase):
    pass


class ProduceListingUpdate(BaseModel):
    crop_id: Optional[str] = None
    variety: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[UnitEnum] = None
    quality_grade: Optional[QualityGrade] = None
    harvest_date: Optional[date] = None
    expected_price: Optional[float] = Field(None, gt=0)
    min_price: Optional[float] = Field(None, gt=0)
    location_name: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    description: Optional[str] = None
    status: Optional[ListingStatus] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class ProduceListingResponse(ProduceListingBase):
    id: str
    seller_id: str
    seller_type: SellerType
    status: ListingStatus
    created_at: datetime
    updated_at: datetime
    crop: Optional[CropResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ProduceListingFilter(BaseModel):
    crop_id: Optional[str] = None
    category: Optional[str] = None
    variety: Optional[str] = None
    quality_grade: Optional[QualityGrade] = None
    seller_type: Optional[SellerType] = None
    status: Optional[ListingStatus] = ListingStatus.ACTIVE
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    # Spatial filter
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = Field(None, gt=0, description="Radius in kilometers")

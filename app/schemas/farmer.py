from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import VerificationStatus


class FarmerProfileBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    phone: Optional[str] = None
    address: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    farm_size: Optional[float] = Field(None, ge=0.0, description="Farm size in acres")
    preferred_crops: Optional[List[str]] = Field(default_factory=list)


class FarmerProfileCreate(FarmerProfileBase):
    pass


class FarmerProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone: Optional[str] = None
    address: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    farm_size: Optional[float] = Field(None, ge=0.0)
    preferred_crops: Optional[List[str]] = None


class FarmerProfileResponse(FarmerProfileBase):
    id: str
    user_id: str
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

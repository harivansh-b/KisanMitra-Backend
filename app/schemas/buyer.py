from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.utils.enums import BuyerType, VerificationStatus


class BuyerProfileBase(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=200)
    buyer_type: BuyerType = Field(default=BuyerType.WHOLESALER)
    contact_person: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(...)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    business_description: Optional[str] = None


class BuyerProfileCreate(BuyerProfileBase):
    pass


class BuyerProfileUpdate(BaseModel):
    organization_name: Optional[str] = Field(None, min_length=2, max_length=200)
    buyer_type: Optional[BuyerType] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    business_description: Optional[str] = None


class BuyerProfileResponse(BuyerProfileBase):
    id: str
    user_id: str
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

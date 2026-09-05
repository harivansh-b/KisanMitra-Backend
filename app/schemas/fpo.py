from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.utils.enums import FPOMemberRole, FPOMemberStatus, VerificationStatus
from app.schemas.farmer import FarmerProfileResponse


class FPOProfileBase(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=200)
    registration_number: str = Field(..., min_length=2, max_length=100)
    contact_person: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(...)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    village_or_city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    description: Optional[str] = None


class FPOProfileCreate(FPOProfileBase):
    pass


class FPOProfileUpdate(BaseModel):
    organization_name: Optional[str] = Field(None, min_length=2, max_length=200)
    registration_number: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    village_or_city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    description: Optional[str] = None


class FPOProfileResponse(FPOProfileBase):
    id: str
    user_id: str
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# FPO Membership Schemas
class FPOMemberAddRequest(BaseModel):
    farmer_id: str = Field(..., description="ID of the farmer profile")
    membership_role: FPOMemberRole = Field(default=FPOMemberRole.MEMBER)


class FPOMemberUpdate(BaseModel):
    membership_role: Optional[FPOMemberRole] = None
    status: Optional[FPOMemberStatus] = None


class FPOMemberResponse(BaseModel):
    id: str
    fpo_id: str
    farmer_id: str
    joined_at: datetime
    status: FPOMemberStatus
    membership_role: FPOMemberRole
    farmer: Optional[FarmerProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)

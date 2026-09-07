from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.utils.enums import UserRole


class TokenPayload(BaseModel):
    sub: str = Field(description="Supabase Auth User ID")
    email: Optional[str] = None
    role: Optional[str] = "authenticated"
    exp: Optional[int] = None


class RegisterProfileRequest(BaseModel):
    role: UserRole = Field(description="Platform role to register: FARMER, FPO, BUYER, STORAGE, TRANSPORT, QUALITY, ADMIN")
    phone: Optional[str] = None
    # Role-specific initial data
    name: Optional[str] = Field(None, description="Used for Farmer/Individual name")
    organization_name: Optional[str] = Field(None, description="Used for FPO, Buyer, Storage, Transport, Quality org name")
    registration_number: Optional[str] = Field(None, description="Registration or License number")
    contact_person: Optional[str] = Field(None, description="Contact person name")
    address: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = Field("Maharashtra", description="State location (defaults to Maharashtra)")
    pincode: Optional[str] = None
    latitude: Optional[float] = Field(18.5204, description="Default latitude (Maharashtra)")
    longitude: Optional[float] = Field(73.8567, description="Default longitude (Maharashtra)")
    farm_size: Optional[float] = None
    buyer_type: Optional[str] = None
    business_description: Optional[str] = None


class UpdateRoleRequest(BaseModel):
    role: UserRole = Field(..., description="New role for the user")
    organization_name: Optional[str] = None
    contact_person: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = "Maharashtra"
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class AuthUserResponse(BaseModel):
    id: str
    auth_user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    profile: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

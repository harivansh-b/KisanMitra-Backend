from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.utils.enums import UserRole


class TokenPayload(BaseModel):
    sub: str = Field(description="Supabase Auth User ID")
    email: Optional[str] = None
    role: Optional[str] = "authenticated"
    exp: Optional[int] = None


class RegisterProfileRequest(BaseModel):
    role: UserRole = Field(description="Platform role to register: FARMER, FPO, or BUYER")
    phone: Optional[str] = None
    # Role-specific initial data
    name: Optional[str] = Field(None, description="Used for Farmer name")
    organization_name: Optional[str] = Field(None, description="Used for FPO or Buyer org name")
    registration_number: Optional[str] = Field(None, description="Required for FPO")
    contact_person: Optional[str] = Field(None, description="Used for FPO or Buyer")
    address: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    farm_size: Optional[float] = None
    buyer_type: Optional[str] = None
    business_description: Optional[str] = None


class AuthUserResponse(BaseModel):
    id: str
    auth_user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    profile: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr

from app.utils.enums import UserRole


class UserBase(BaseModel):
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    role: UserRole


class UserCreate(UserBase):
    auth_user_id: str


class UserUpdate(BaseModel):
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: str
    auth_user_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

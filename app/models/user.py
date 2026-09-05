import uuid
from sqlalchemy import Boolean, Column, DateTime, Enum, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    auth_user_id = Column(String(100), unique=True, nullable=False, index=True)
    role = Column(Enum(UserRole), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(150), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 1-to-1 profile relationships
    farmer_profile = relationship("FarmerProfile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    fpo_profile = relationship("FPOProfile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    buyer_profile = relationship("BuyerProfile", uselist=False, back_populates="user", cascade="all, delete-orphan")

    # Documents
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")

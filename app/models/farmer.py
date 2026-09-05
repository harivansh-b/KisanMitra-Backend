import uuid
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, JSON, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base, PointGeography
from app.utils.enums import VerificationStatus


class FarmerProfile(Base):
    __tablename__ = "farmer_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    village = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    pincode = Column(String(10), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location = Column(PointGeography(), nullable=True)
    farm_size = Column(Float, nullable=True)  # in acres
    preferred_crops = Column(JSON, default=list, nullable=True)
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="farmer_profile")
    fpo_memberships = relationship("FPOMember", back_populates="farmer", cascade="all, delete-orphan")

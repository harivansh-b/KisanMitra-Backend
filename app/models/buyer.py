import uuid
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import foreign, relationship

from app.core.database import Base, PointGeography
from app.utils.enums import BuyerType, VerificationStatus


class BuyerProfile(Base):
    __tablename__ = "buyer_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    organization_name = Column(String(200), nullable=False, index=True)
    buyer_type = Column(Enum(BuyerType), default=BuyerType.WHOLESALER, nullable=False)
    contact_person = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(150), nullable=True)
    address = Column(String(255), nullable=True)
    location_name = Column(String(150), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location = Column(PointGeography(), nullable=True)
    business_description = Column(Text, nullable=True)
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="buyer_profile")
    requirements = relationship(
        "BuyerRequirement",
        primaryjoin="BuyerProfile.user_id == foreign(BuyerRequirement.buyer_id)",
        back_populates="buyer",
        cascade="all, delete-orphan",
    )

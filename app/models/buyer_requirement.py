import uuid
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import foreign, relationship

from app.core.database import Base, PointGeography
from app.utils.enums import QualityGrade, RequirementStatus, UnitEnum


class BuyerRequirement(Base):
    __tablename__ = "buyer_requirements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    buyer_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    crop_id = Column(String(36), ForeignKey("crops.id", ondelete="RESTRICT"), nullable=False, index=True)
    variety = Column(String(100), nullable=True, index=True)
    required_quantity = Column(Float, nullable=False)
    unit = Column(Enum(UnitEnum), default=UnitEnum.QUINTAL, nullable=False)
    quality_grade = Column(Enum(QualityGrade), nullable=True)
    target_price = Column(Float, nullable=False)
    delivery_location = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location = Column(PointGeography(), nullable=True)
    required_from = Column(DateTime(timezone=True), nullable=True)
    required_until = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(RequirementStatus), default=RequirementStatus.ACTIVE, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    buyer = relationship(
        "BuyerProfile",
        primaryjoin="foreign(BuyerRequirement.buyer_id) == BuyerProfile.user_id",
        back_populates="requirements",
    )
    buyer_user = relationship("User", foreign_keys=[buyer_id], overlaps="buyer,requirements")
    crop = relationship("Crop", back_populates="requirements")

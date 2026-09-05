import uuid
from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base, PointGeography
from app.utils.enums import ListingStatus, QualityGrade, SellerType, UnitEnum


class ProduceListing(Base):
    __tablename__ = "produce_listings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    seller_type = Column(Enum(SellerType), nullable=False, index=True)
    crop_id = Column(String(36), ForeignKey("crops.id", ondelete="RESTRICT"), nullable=False, index=True)
    variety = Column(String(100), nullable=True, index=True)
    quantity = Column(Float, nullable=False)
    unit = Column(Enum(UnitEnum), default=UnitEnum.QUINTAL, nullable=False)
    quality_grade = Column(Enum(QualityGrade), default=QualityGrade.GRADE_A, nullable=False)
    harvest_date = Column(Date, nullable=True)
    expected_price = Column(Float, nullable=False)
    min_price = Column(Float, nullable=True)
    location_name = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location = Column(PointGeography(), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(ListingStatus), default=ListingStatus.ACTIVE, nullable=False, index=True)
    available_from = Column(DateTime(timezone=True), nullable=True)
    available_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    seller = relationship("User", foreign_keys=[seller_id])
    crop = relationship("Crop", back_populates="listings")
    orders = relationship("Order", back_populates="listing")

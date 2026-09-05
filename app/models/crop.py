import uuid
from sqlalchemy import Boolean, Column, DateTime, Enum, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.enums import UnitEnum


class Crop(Base):
    __tablename__ = "crops"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    local_name = Column(String(100), nullable=True)
    category = Column(String(50), nullable=False, index=True)  # e.g., CEREALS, PULSES, VEGETABLES, FRUITS, OILSEEDS
    variety = Column(String(100), nullable=True)
    default_unit = Column(Enum(UnitEnum), default=UnitEnum.QUINTAL, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    listings = relationship("ProduceListing", back_populates="crop")
    requirements = relationship("BuyerRequirement", back_populates="crop")

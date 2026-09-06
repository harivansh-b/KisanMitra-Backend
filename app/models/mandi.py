import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base, PointGeography


class Mandi(Base):
    __tablename__ = "mandis"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, index=True)
    market_code = Column(String(50), nullable=True, index=True)
    state = Column(String(100), nullable=False, default="Maharashtra", index=True)
    district = Column(String(100), nullable=False, index=True)
    taluk = Column(String(100), nullable=True, index=True)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location = Column(PointGeography(), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    source = Column(String(100), nullable=True)  # e.g. "AGMARKNET", "eNAM", "MANUAL"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    prices = relationship("MandiPrice", back_populates="mandi", cascade="all, delete-orphan")

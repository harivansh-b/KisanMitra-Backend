import uuid
from sqlalchemy import (
    CheckConstraint, Column, Date, DateTime, Float, ForeignKey,
    String, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class MandiPrice(Base):
    __tablename__ = "mandi_prices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mandi_id = Column(String(36), ForeignKey("mandis.id", ondelete="CASCADE"), nullable=False, index=True)
    commodity_id = Column(String(36), ForeignKey("crops.id", ondelete="SET NULL"), nullable=True, index=True)
    commodity_name = Column(String(150), nullable=False, index=True)   # raw name from source
    variety = Column(String(100), nullable=True, index=True)
    grade = Column(String(50), nullable=True)
    arrival_date = Column(Date, nullable=False, index=True)
    arrival_quantity = Column(Float, nullable=True)
    arrival_unit = Column(String(20), nullable=True, default="Quintal")
    min_price = Column(Float, nullable=False)      # INR per Quintal
    max_price = Column(Float, nullable=False)
    modal_price = Column(Float, nullable=False)    # most commonly traded price
    price_unit = Column(String(30), nullable=False, default="INR/Quintal")
    source = Column(String(100), nullable=False, default="AGMARKNET")
    source_record_id = Column(String(200), nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "mandi_id", "commodity_name", "variety", "grade", "arrival_date", "source",
            name="uq_mandi_price_record",
        ),
        CheckConstraint("min_price >= 0", name="ck_mandi_price_min_positive"),
        CheckConstraint("max_price >= 0", name="ck_mandi_price_max_positive"),
        CheckConstraint("modal_price >= 0", name="ck_mandi_price_modal_positive"),
        CheckConstraint(
            "arrival_quantity IS NULL OR arrival_quantity >= 0",
            name="ck_mandi_arrival_qty_positive",
        ),
        CheckConstraint("min_price <= modal_price", name="ck_mandi_price_min_le_modal"),
        CheckConstraint("modal_price <= max_price", name="ck_mandi_price_modal_le_max"),
    )

    mandi = relationship("Mandi", back_populates="prices")
    crop = relationship("Crop", foreign_keys=[commodity_id])

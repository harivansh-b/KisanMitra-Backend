import uuid
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.enums import TransactionStatus


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    buyer_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    seller_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    listing_id = Column(String(36), ForeignKey("produce_listings.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Float, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.INITIATED, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    order = relationship("Order", back_populates="transactions")
    buyer = relationship("User", foreign_keys=[buyer_id])
    seller = relationship("User", foreign_keys=[seller_id])

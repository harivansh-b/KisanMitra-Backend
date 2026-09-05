from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import TransactionStatus


class TransactionCreate(BaseModel):
    order_id: Optional[str] = None
    buyer_id: str
    seller_id: str
    listing_id: Optional[str] = None
    quantity: float = Field(..., gt=0)
    price_per_unit: float = Field(..., gt=0)
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    order_id: Optional[str] = None
    buyer_id: str
    seller_id: str
    listing_id: Optional[str] = None
    quantity: float
    price_per_unit: float
    total_amount: float
    status: TransactionStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

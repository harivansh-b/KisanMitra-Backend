from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import OrderStatus
from app.schemas.listing import ProduceListingResponse


class OrderCreate(BaseModel):
    listing_id: str
    quantity: float = Field(..., gt=0)
    agreed_price: Optional[float] = Field(None, gt=0, description="Agreed price per unit; defaults to listing price if omitted")
    delivery_location: Optional[str] = None
    notes: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus = Field(..., description="Target status: ACCEPTED, CONFIRMED, COMPLETED, REJECTED, CANCELLED")


class OrderResponse(BaseModel):
    id: str
    buyer_id: str
    seller_id: str
    listing_id: str
    quantity: float
    agreed_price: float
    total_amount: float
    status: OrderStatus
    delivery_location: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    listing: Optional[ProduceListingResponse] = None

    model_config = ConfigDict(from_attributes=True)

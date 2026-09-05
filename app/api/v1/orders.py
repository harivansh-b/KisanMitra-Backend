from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_buyer, get_current_user, get_db
from app.models.user import User
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services.order_service import order_service
from app.utils.enums import OrderStatus
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/orders", tags=["Orders & Purchase Requests"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_request(
    data: OrderCreate,
    current_user: User = Depends(get_current_buyer),
    db: Session = Depends(get_db),
):
    """Create a new purchase request against an active marketplace listing (Buyers only)."""
    return order_service.create_order(db, current_user, data)


@router.get("", response_model=PaginatedResponse[OrderResponse])
def list_orders(
    status: Optional[OrderStatus] = Query(None, description="Filter by order status"),
    as_role: Optional[str] = Query(None, description="'buyer' or 'seller'"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List orders for the logged-in user with role filtering and pagination."""
    params = PaginationParams(page=page, page_size=page_size)
    orders, total = order_service.list_orders(
        db,
        current_user=current_user,
        status=status,
        as_role=as_role,
        offset=params.offset,
        limit=params.limit,
    )
    return PaginatedResponse.create(orders, total, params)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve details of a specific purchase request/order."""
    return order_service.get_order_by_id(db, order_id, current_user)


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: str,
    data: OrderStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Transition order state along its lifecycle:
    - Seller can ACCEPT or REJECT a PENDING order.
    - Buyer can CANCEL a PENDING order.
    - Buyer/Seller can CONFIRM an ACCEPTED order (creates transaction ledger entry).
    - Buyer/Seller can mark a CONFIRMED order as COMPLETED.
    """
    return order_service.update_order_status(db, order_id, current_user, data)

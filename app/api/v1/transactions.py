from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionResponse
from app.services.transaction_service import transaction_service
from app.utils.enums import TransactionStatus
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=PaginatedResponse[TransactionResponse])
def list_transactions(
    status: Optional[TransactionStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List financial/settlement records for the authenticated user."""
    params = PaginationParams(page=page, page_size=page_size)
    txns, total = transaction_service.list_transactions(
        db, current_user=current_user, status=status, offset=params.offset, limit=params.limit
    )
    return PaginatedResponse.create(txns, total, params)


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve details for a specific marketplace transaction."""
    return transaction_service.get_transaction_by_id(db, transaction_id, current_user)


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new transaction record directly."""
    return transaction_service.create_transaction(db, current_user, data)

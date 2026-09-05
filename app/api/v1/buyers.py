from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_buyer, get_current_user, get_db
from app.models.user import User
from app.schemas.buyer import BuyerProfileResponse, BuyerProfileUpdate
from app.services.buyer_service import buyer_service

router = APIRouter(prefix="/buyers", tags=["Buyers"])


@router.get("/me", response_model=BuyerProfileResponse)
def get_my_buyer_profile(
    current_user: User = Depends(get_current_buyer),
    db: Session = Depends(get_db),
):
    """Retrieve the logged-in buyer's profile."""
    return buyer_service.get_profile_by_user_id(db, current_user.id)


@router.put("/me", response_model=BuyerProfileResponse)
def update_my_buyer_profile(
    data: BuyerProfileUpdate,
    current_user: User = Depends(get_current_buyer),
    db: Session = Depends(get_db),
):
    """Update the logged-in buyer's profile and sourcing preferences."""
    profile = buyer_service.get_profile_by_user_id(db, current_user.id)
    return buyer_service.update_profile(db, profile, data)


@router.get("/{buyer_id}", response_model=BuyerProfileResponse)
def get_buyer_public_profile(
    buyer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get public profile of a buyer."""
    return buyer_service.get_buyer_by_id(db, buyer_id)

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer, get_current_user, get_db
from app.models.user import User
from app.schemas.buyer import BuyerProfileResponse
from app.schemas.farmer import FarmerProfileResponse, FarmerProfileUpdate
from app.schemas.fpo import FPOProfileResponse
from app.schemas.requirement import BuyerRequirementResponse
from app.services.farmer_service import farmer_service
from app.services.marketplace_service import marketplace_service

router = APIRouter(prefix="/farmers", tags=["Farmers"])


@router.get("/me", response_model=FarmerProfileResponse)
def get_my_farmer_profile(
    current_user: User = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Retrieve the logged-in farmer's profile."""
    return farmer_service.get_profile_by_user_id(db, current_user.id)


@router.put("/me", response_model=FarmerProfileResponse)
def update_my_farmer_profile(
    data: FarmerProfileUpdate,
    current_user: User = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Update the logged-in farmer's profile and farm location."""
    profile = farmer_service.get_profile_by_user_id(db, current_user.id)
    return farmer_service.update_profile(db, profile, data)


@router.get("/me/relevant-fpos", response_model=List[FPOProfileResponse])
def get_relevant_fpos(
    radius_km: float = Query(50.0, ge=1.0, le=500.0, description="Search radius in kilometers"),
    current_user: User = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """List FPOs near the farmer's location for aggregation and membership."""
    profile = farmer_service.get_profile_by_user_id(db, current_user.id)
    return farmer_service.get_relevant_fpos(db, profile, radius_km)


@router.get("/me/relevant-buyers", response_model=List[BuyerProfileResponse])
def get_relevant_buyers(
    radius_km: float = Query(100.0, ge=1.0, le=1000.0, description="Search radius in kilometers"),
    current_user: User = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """List buyers near the farmer's location."""
    profile = farmer_service.get_profile_by_user_id(db, current_user.id)
    return farmer_service.get_relevant_buyers(db, profile, radius_km)


@router.get("/{farmer_id}", response_model=FarmerProfileResponse)
def get_farmer_public_profile(
    farmer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get public profile of a farmer."""
    return farmer_service.get_farmer_by_id(db, farmer_id)

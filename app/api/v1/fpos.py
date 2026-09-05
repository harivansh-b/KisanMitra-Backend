from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_fpo, get_current_user, get_db
from app.models.user import User
from app.schemas.fpo import (
    FPOMemberAddRequest,
    FPOMemberResponse,
    FPOMemberUpdate,
    FPOProfileResponse,
    FPOProfileUpdate,
)
from app.services.fpo_service import fpo_service
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/fpos", tags=["FPOs"])


@router.get("/me", response_model=FPOProfileResponse)
def get_my_fpo_profile(
    current_user: User = Depends(get_current_fpo),
    db: Session = Depends(get_db),
):
    """Retrieve the logged-in FPO's profile."""
    return fpo_service.get_profile_by_user_id(db, current_user.id)


@router.put("/me", response_model=FPOProfileResponse)
def update_my_fpo_profile(
    data: FPOProfileUpdate,
    current_user: User = Depends(get_current_fpo),
    db: Session = Depends(get_db),
):
    """Update the logged-in FPO's profile."""
    profile = fpo_service.get_profile_by_user_id(db, current_user.id)
    return fpo_service.update_profile(db, profile, data)


@router.get("/members", response_model=PaginatedResponse[FPOMemberResponse])
def list_fpo_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_fpo),
    db: Session = Depends(get_db),
):
    """List members of the logged-in FPO."""
    fpo = fpo_service.get_profile_by_user_id(db, current_user.id)
    params = PaginationParams(page=page, page_size=page_size)
    members, total = fpo_service.list_members(db, fpo, offset=params.offset, limit=params.limit)
    return PaginatedResponse.create(members, total, params)


@router.post("/members", response_model=FPOMemberResponse, status_code=status.HTTP_201_CREATED)
def add_farmer_to_fpo(
    req: FPOMemberAddRequest,
    current_user: User = Depends(get_current_fpo),
    db: Session = Depends(get_db),
):
    """Add a farmer to the FPO's membership registry."""
    fpo = fpo_service.get_profile_by_user_id(db, current_user.id)
    return fpo_service.add_member(db, fpo, req)


@router.patch("/members/{farmer_id}", response_model=FPOMemberResponse)
def update_fpo_member(
    farmer_id: str,
    data: FPOMemberUpdate,
    current_user: User = Depends(get_current_fpo),
    db: Session = Depends(get_db),
):
    """Update role or status of an FPO member."""
    fpo = fpo_service.get_profile_by_user_id(db, current_user.id)
    return fpo_service.update_member(db, fpo, farmer_id, data)


@router.delete("/members/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_farmer_from_fpo(
    farmer_id: str,
    current_user: User = Depends(get_current_fpo),
    db: Session = Depends(get_db),
):
    """Remove a farmer from the FPO."""
    fpo = fpo_service.get_profile_by_user_id(db, current_user.id)
    fpo_service.remove_member(db, fpo, farmer_id)


@router.get("/{fpo_id}", response_model=FPOProfileResponse)
def get_fpo_public_profile(
    fpo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get public profile of an FPO."""
    return fpo_service.get_fpo_by_id(db, fpo_id)

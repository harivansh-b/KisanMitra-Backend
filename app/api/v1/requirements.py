from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_buyer, get_current_user, get_db
from app.models.user import User
from app.schemas.requirement import (
    BuyerRequirementCreate,
    BuyerRequirementFilter,
    BuyerRequirementResponse,
    BuyerRequirementUpdate,
)
from app.services.requirement_service import requirement_service
from app.utils.enums import QualityGrade, RequirementStatus
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/requirements", tags=["Buyer Requirements"])


@router.post("", response_model=BuyerRequirementResponse, status_code=status.HTTP_201_CREATED)
def create_requirement(
    data: BuyerRequirementCreate,
    current_user: User = Depends(get_current_buyer),
    db: Session = Depends(get_db),
):
    """Post a sourcing demand requirement (Buyers only)."""
    return requirement_service.create_requirement(db, current_user, data)


@router.get("", response_model=PaginatedResponse[BuyerRequirementResponse])
def list_requirements(
    crop_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    variety: Optional[str] = Query(None),
    quality_grade: Optional[QualityGrade] = Query(None),
    status: Optional[RequirementStatus] = Query(RequirementStatus.ACTIVE),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_quantity: Optional[float] = Query(None),
    max_quantity: Optional[float] = Query(None),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    radius_km: Optional[float] = Query(None, gt=0, description="PostGIS search radius in km"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search active buyer requirements with optional PostGIS geo-filtering."""
    filters = BuyerRequirementFilter(
        crop_id=crop_id,
        category=category,
        variety=variety,
        quality_grade=quality_grade,
        status=status,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
    )
    params = PaginationParams(page=page, page_size=page_size)
    requirements, total = requirement_service.list_requirements(
        db, filters, offset=params.offset, limit=params.limit
    )
    return PaginatedResponse.create(requirements, total, params)


@router.get("/me", response_model=PaginatedResponse[BuyerRequirementResponse])
def list_my_requirements(
    status: Optional[RequirementStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_buyer),
    db: Session = Depends(get_db),
):
    """Retrieve all requirements posted by the authenticated buyer."""
    params = PaginationParams(page=page, page_size=page_size)
    requirements, total = requirement_service.list_buyer_requirements(
        db, current_user.id, offset=params.offset, limit=params.limit, status=status
    )
    return PaginatedResponse.create(requirements, total, params)


@router.get("/{requirement_id}", response_model=BuyerRequirementResponse)
def get_requirement(
    requirement_id: str,
    db: Session = Depends(get_db),
):
    """Get details of a specific buyer requirement."""
    return requirement_service.get_requirement_by_id(db, requirement_id)


@router.put("/{requirement_id}", response_model=BuyerRequirementResponse)
def update_requirement(
    requirement_id: str,
    data: BuyerRequirementUpdate,
    current_user: User = Depends(get_current_buyer),
    db: Session = Depends(get_db),
):
    """Update a buyer requirement (only allowed for requirement owner)."""
    return requirement_service.update_requirement(db, requirement_id, current_user, data)


@router.delete("/{requirement_id}", response_model=BuyerRequirementResponse)
def cancel_requirement(
    requirement_id: str,
    current_user: User = Depends(get_current_buyer),
    db: Session = Depends(get_db),
):
    """Cancel a buyer requirement (sets status to CANCELLED)."""
    return requirement_service.cancel_requirement(db, requirement_id, current_user)

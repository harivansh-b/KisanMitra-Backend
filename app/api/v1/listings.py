from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_seller, get_current_user, get_db
from app.models.user import User
from app.schemas.listing import (
    ProduceListingCreate,
    ProduceListingFilter,
    ProduceListingResponse,
    ProduceListingUpdate,
)
from app.services.listing_service import listing_service
from app.utils.enums import ListingStatus, QualityGrade, SellerType
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/listings", tags=["Produce Listings"])


@router.post("", response_model=ProduceListingResponse, status_code=status.HTTP_201_CREATED)
def create_listing(
    data: ProduceListingCreate,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    """Create a new produce lot listing on the marketplace (Farmers and FPOs only)."""
    return listing_service.create_listing(db, current_user, data)


@router.get("", response_model=PaginatedResponse[ProduceListingResponse])
def list_listings(
    crop_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    variety: Optional[str] = Query(None),
    quality_grade: Optional[QualityGrade] = Query(None),
    seller_type: Optional[SellerType] = Query(None),
    status: Optional[ListingStatus] = Query(ListingStatus.ACTIVE),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_quantity: Optional[float] = Query(None),
    max_quantity: Optional[float] = Query(None),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    radius_km: Optional[float] = Query(None, gt=0, description="PostGIS radius distance search in km"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search and filter available produce listings with optional PostGIS geo-radius filtering."""
    filters = ProduceListingFilter(
        crop_id=crop_id,
        category=category,
        variety=variety,
        quality_grade=quality_grade,
        seller_type=seller_type,
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
    listings, total = listing_service.list_listings(db, filters, offset=params.offset, limit=params.limit)
    return PaginatedResponse.create(listings, total, params)


@router.get("/me", response_model=PaginatedResponse[ProduceListingResponse])
def list_my_listings(
    status: Optional[ListingStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    """Retrieve all listings created by the authenticated seller."""
    params = PaginationParams(page=page, page_size=page_size)
    listings, total = listing_service.list_seller_listings(
        db, current_user.id, offset=params.offset, limit=params.limit, status=status
    )
    return PaginatedResponse.create(listings, total, params)


@router.get("/{listing_id}", response_model=ProduceListingResponse)
def get_listing(
    listing_id: str,
    db: Session = Depends(get_db),
):
    """Get complete details for a single produce listing."""
    return listing_service.get_listing_by_id(db, listing_id)


@router.put("/{listing_id}", response_model=ProduceListingResponse)
def update_listing(
    listing_id: str,
    data: ProduceListingUpdate,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    """Update an existing produce listing (only allowed for the listing owner)."""
    return listing_service.update_listing(db, listing_id, current_user, data)


@router.delete("/{listing_id}", response_model=ProduceListingResponse)
def cancel_listing(
    listing_id: str,
    current_user: User = Depends(get_current_seller),
    db: Session = Depends(get_db),
):
    """Cancel a produce listing (sets status to CANCELLED)."""
    return listing_service.cancel_listing(db, listing_id, current_user)

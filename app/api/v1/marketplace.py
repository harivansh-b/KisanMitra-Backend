from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.listing import ProduceListingFilter, ProduceListingResponse
from app.schemas.requirement import BuyerRequirementFilter, BuyerRequirementResponse
from app.services.listing_service import listing_service
from app.services.marketplace_service import marketplace_service
from app.services.requirement_service import requirement_service
from app.utils.enums import ListingStatus, QualityGrade, RequirementStatus, SellerType
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


@router.get("/listings", response_model=PaginatedResponse[ProduceListingResponse])
def marketplace_search_listings(
    crop_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    variety: Optional[str] = Query(None),
    quality_grade: Optional[QualityGrade] = Query(None),
    seller_type: Optional[SellerType] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_quantity: Optional[float] = Query(None),
    max_quantity: Optional[float] = Query(None),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    radius_km: Optional[float] = Query(None, gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Public marketplace browsing endpoint for active produce lots."""
    filters = ProduceListingFilter(
        crop_id=crop_id,
        category=category,
        variety=variety,
        quality_grade=quality_grade,
        seller_type=seller_type,
        status=ListingStatus.ACTIVE,
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


@router.get("/requirements", response_model=PaginatedResponse[BuyerRequirementResponse])
def marketplace_search_requirements(
    crop_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    variety: Optional[str] = Query(None),
    quality_grade: Optional[QualityGrade] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_quantity: Optional[float] = Query(None),
    max_quantity: Optional[float] = Query(None),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    radius_km: Optional[float] = Query(None, gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Public marketplace browsing endpoint for active buyer sourcing demands."""
    filters = BuyerRequirementFilter(
        crop_id=crop_id,
        category=category,
        variety=variety,
        quality_grade=quality_grade,
        status=RequirementStatus.ACTIVE,
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


@router.get("/match-listings-for-requirement/{requirement_id}", response_model=List[ProduceListingResponse])
def match_listings_for_requirement(
    requirement_id: str,
    radius_km: Optional[float] = Query(200.0, gt=0, description="PostGIS search radius in km"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Rule-based matching: find produce listings matching a specific buyer requirement."""
    return marketplace_service.match_listings_for_requirement(
        db, requirement_id=requirement_id, radius_km=radius_km, limit=limit
    )


@router.get("/match-requirements-for-listing/{listing_id}", response_model=List[BuyerRequirementResponse])
def match_requirements_for_listing(
    listing_id: str,
    radius_km: Optional[float] = Query(200.0, gt=0, description="PostGIS search radius in km"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Rule-based matching: find active buyer sourcing demands matching a specific seller listing."""
    return marketplace_service.match_requirements_for_listing(
        db, listing_id=listing_id, radius_km=radius_km, limit=limit
    )

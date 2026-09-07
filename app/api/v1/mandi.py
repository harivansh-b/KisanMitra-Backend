from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.mandi import (
    MandiResponse,
    MandiPriceFilter,
    MandiPriceResponse,
    NearbyMandiResult,
)
from app.services.mandi_service import mandi_service
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/mandi", tags=["Mandi / Market Intelligence"])
# Canonical market-resource aliases retained alongside the established
# /mandi namespace so external clients can use /api/v1/mandis/{id}.
market_router = APIRouter(prefix="/mandis", tags=["Mandi / Market Intelligence"])


@router.get("/mandis", response_model=PaginatedResponse[MandiResponse])
def list_mandis(
    district: Optional[str] = Query(None, description="Filter by district name"),
    state: Optional[str] = Query(None, description="Filter by state name"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List Maharashtra agricultural mandis with optional district filter."""
    params = PaginationParams(page=page, page_size=page_size)
    mandis, total = mandi_service.list_mandis(
        db,
        district=district,
        state=state,
        is_active=is_active,
        offset=params.offset,
        limit=params.limit,
    )
    return PaginatedResponse.create(mandis, total, params)


@router.get("/mandis/{mandi_id}/prices", response_model=PaginatedResponse[MandiPriceResponse])
def get_mandi_prices(
    mandi_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get all available prices for a specific mandi."""
    params = PaginationParams(page=page, page_size=page_size)
    prices, total = mandi_service.list_mandi_prices(
        db, mandi_id=mandi_id, offset=params.offset, limit=params.limit
    )
    return PaginatedResponse.create(prices, total, params)


@router.get("/mandis/{mandi_id}", response_model=MandiResponse)
def get_mandi(
    mandi_id: str,
    db: Session = Depends(get_db),
):
    """Get details for a single mandi by ID."""
    return mandi_service.get_mandi_by_id(db, mandi_id)


@router.get("/prices/latest", response_model=List[MandiPriceResponse])
def get_latest_prices(
    commodity: Optional[str] = Query(None, description="Filter by commodity name (partial match)"),
    district: Optional[str] = Query(None, description="Filter by district name"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Return the latest available price record per mandi+commodity combination.
    Useful for building a real-time price board.
    """
    return mandi_service.latest_prices(db, commodity=commodity, district=district, limit=limit)


@router.get("/prices", response_model=PaginatedResponse[MandiPriceResponse])
def list_prices(
    mandi_id: Optional[str] = Query(None),
    district: Optional[str] = Query(None, description="Filter by district (partial match)"),
    commodity: Optional[str] = Query(None, description="Filter by commodity name (partial match)"),
    variety: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Search and filter mandi price records with pagination."""
    filters = MandiPriceFilter(
        mandi_id=mandi_id,
        district=district,
        commodity=commodity,
        variety=variety,
        from_date=from_date,
        to_date=to_date,
        min_price=min_price,
        max_price=max_price,
    )
    params = PaginationParams(page=page, page_size=page_size)
    prices, total = mandi_service.list_prices(db, filters, offset=params.offset, limit=params.limit)
    return PaginatedResponse.create(prices, total, params)


@router.get("/nearby", response_model=List[NearbyMandiResult])
def nearby_mandis(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Observer latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Observer longitude"),
    radius_km: float = Query(100.0, gt=0, le=500.0, description="Search radius in kilometers"),
    commodity: Optional[str] = Query(None, description="Only return mandis trading this commodity"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Find nearby mandis using PostGIS ST_DWithin spatial query.
    Results are ordered by distance (nearest first).
    Returns distance_km alongside mandi details.
    """
    results = mandi_service.nearby_mandis(
        db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        commodity=commodity,
        limit=limit,
    )
    return results


@market_router.get("", response_model=PaginatedResponse[MandiResponse])
def list_market_resources(
    district: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_mandis(district, state, is_active, page, page_size, db)


@market_router.get("/{mandi_id}", response_model=MandiResponse)
def get_market_resource(mandi_id: str, db: Session = Depends(get_db)):
    return get_mandi(mandi_id, db)


@market_router.get("/{mandi_id}/prices", response_model=PaginatedResponse[MandiPriceResponse])
def get_market_resource_prices(
    mandi_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return get_mandi_prices(mandi_id, page, page_size, db)

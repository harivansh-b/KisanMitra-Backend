from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.crop import CropCreate, CropResponse, CropUpdate
from app.services.crop_service import crop_service
from app.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/crops", tags=["Crops"])


@router.get("", response_model=PaginatedResponse[CropResponse])
def list_crops(
    category: Optional[str] = Query(None, description="Filter by crop category (e.g., CEREALS, PULSES)"),
    search: Optional[str] = Query(None, description="Search by crop name or local name"),
    is_active: Optional[bool] = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all registered crops with category filtering and name search."""
    params = PaginationParams(page=page, page_size=page_size)
    crops, total = crop_service.list_crops(
        db=db,
        category=category,
        search=search,
        is_active=is_active,
        offset=params.offset,
        limit=params.limit,
    )
    return PaginatedResponse.create(crops, total, params)


@router.get("/{crop_id}", response_model=CropResponse)
def get_crop(
    crop_id: str,
    db: Session = Depends(get_db),
):
    """Get crop master details by ID."""
    return crop_service.get_crop_by_id(db, crop_id)


@router.post("", response_model=CropResponse, status_code=status.HTTP_201_CREATED)
def create_crop(
    data: CropCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new crop master entry."""
    return crop_service.create_crop(db, data)


@router.put("/{crop_id}", response_model=CropResponse)
def update_crop(
    crop_id: str,
    data: CropUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update crop master details."""
    return crop_service.update_crop(db, crop_id, data)


@router.post("/seed/defaults", status_code=status.HTTP_200_OK)
def seed_default_crops(
    db: Session = Depends(get_db),
):
    """Seeds default common Indian crops if the database table is empty."""
    count = crop_service.seed_default_crops(db)
    return {"message": f"Successfully seeded {count} default crops."}

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.crop import Crop
from app.models.produce_listing import ProduceListing
from app.models.user import User
from app.schemas.listing import ProduceListingCreate, ProduceListingFilter, ProduceListingUpdate
from app.services.geo_service import geo_service
from app.utils.enums import ListingStatus, SellerType, UserRole


class ListingService:
    @staticmethod
    def get_listing_by_id(db: Session, listing_id: str) -> ProduceListing:
        listing = (
            db.query(ProduceListing)
            .options(joinedload(ProduceListing.crop))
            .filter(ProduceListing.id == listing_id)
            .first()
        )
        if not listing:
            raise NotFoundException(f"Listing with ID '{listing_id}' not found")
        return listing

    @staticmethod
    def create_listing(db: Session, user: User, data: ProduceListingCreate) -> ProduceListing:
        # Validate seller type
        if user.role not in [UserRole.FARMER, UserRole.FPO]:
            raise ForbiddenException("Only Farmers or FPOs can create produce listings.")

        # Validate crop
        crop = db.query(Crop).filter(Crop.id == data.crop_id, Crop.is_active == True).first()
        if not crop:
            raise NotFoundException(f"Active crop with ID '{data.crop_id}' not found.")

        seller_type = SellerType.FARMER if user.role == UserRole.FARMER else SellerType.FPO
        location_geom = geo_service.create_point_wkt(data.latitude, data.longitude)

        listing = ProduceListing(
            seller_id=user.id,
            seller_type=seller_type,
            crop_id=data.crop_id,
            variety=data.variety,
            quantity=data.quantity,
            unit=data.unit,
            quality_grade=data.quality_grade,
            harvest_date=data.harvest_date,
            expected_price=data.expected_price,
            min_price=data.min_price or data.expected_price,
            location_name=data.location_name,
            latitude=data.latitude,
            longitude=data.longitude,
            location=location_geom,
            description=data.description,
            status=ListingStatus.ACTIVE,
            available_from=data.available_from,
            available_until=data.available_until,
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def update_listing(db: Session, listing_id: str, user: User, data: ProduceListingUpdate) -> ProduceListing:
        listing = ListingService.get_listing_by_id(db, listing_id)

        # Ownership authorization
        if listing.seller_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenException("You do not have permission to modify this listing.")

        update_dict = data.model_dump(exclude_unset=True)

        if "crop_id" in update_dict and update_dict["crop_id"] != listing.crop_id:
            crop = db.query(Crop).filter(Crop.id == update_dict["crop_id"], Crop.is_active == True).first()
            if not crop:
                raise NotFoundException(f"Active crop with ID '{update_dict['crop_id']}' not found.")

        for key, value in update_dict.items():
            setattr(listing, key, value)

        if "latitude" in update_dict or "longitude" in update_dict:
            listing.location = geo_service.create_point_wkt(listing.latitude, listing.longitude)

        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def cancel_listing(db: Session, listing_id: str, user: User) -> ProduceListing:
        listing = ListingService.get_listing_by_id(db, listing_id)
        if listing.seller_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenException("You do not have permission to cancel this listing.")

        listing.status = ListingStatus.CANCELLED
        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def list_listings(
        db: Session,
        filters: ProduceListingFilter,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[ProduceListing], int]:
        query = db.query(ProduceListing).options(joinedload(ProduceListing.crop))

        if filters.status:
            query = query.filter(ProduceListing.status == filters.status)
        if filters.crop_id:
            query = query.filter(ProduceListing.crop_id == filters.crop_id)
        if filters.variety:
            query = query.filter(ProduceListing.variety.ilike(f"%{filters.variety}%"))
        if filters.quality_grade:
            query = query.filter(ProduceListing.quality_grade == filters.quality_grade)
        if filters.seller_type:
            query = query.filter(ProduceListing.seller_type == filters.seller_type)
        if filters.min_price is not None:
            query = query.filter(ProduceListing.expected_price >= filters.min_price)
        if filters.max_price is not None:
            query = query.filter(ProduceListing.expected_price <= filters.max_price)
        if filters.min_quantity is not None:
            query = query.filter(ProduceListing.quantity >= filters.min_quantity)
        if filters.max_quantity is not None:
            query = query.filter(ProduceListing.quantity <= filters.max_quantity)

        # PostGIS / Geo Radius Filter
        if filters.latitude is not None and filters.longitude is not None and filters.radius_km:
            is_pg = db.bind.dialect.name == "postgresql"
            query = geo_service.apply_radius_filter(
                query, ProduceListing, filters.latitude, filters.longitude, filters.radius_km, is_postgresql=is_pg
            )

        total = query.count()
        listings = query.order_by(ProduceListing.created_at.desc()).offset(offset).limit(limit).all()
        return listings, total

    @staticmethod
    def list_seller_listings(
        db: Session,
        seller_id: str,
        offset: int = 0,
        limit: int = 20,
        status: Optional[ListingStatus] = None,
    ) -> Tuple[List[ProduceListing], int]:
        query = (
            db.query(ProduceListing)
            .options(joinedload(ProduceListing.crop))
            .filter(ProduceListing.seller_id == seller_id)
        )
        if status:
            query = query.filter(ProduceListing.status == status)

        total = query.count()
        listings = query.order_by(ProduceListing.created_at.desc()).offset(offset).limit(limit).all()
        return listings, total


listing_service = ListingService()

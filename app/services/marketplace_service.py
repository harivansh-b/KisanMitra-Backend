from typing import List, Optional
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundException
from app.models.buyer_requirement import BuyerRequirement
from app.models.produce_listing import ProduceListing
from app.services.geo_service import geo_service
from app.utils.enums import ListingStatus, RequirementStatus


class MarketplaceService:
    """
    Isolated rule-based deterministic matching engine between produce listings
    and buyer requirements. Designed to be easily augmented or replaced by ML/Recommendation
    services in future sprints.
    """

    @staticmethod
    def match_listings_for_requirement(
        db: Session,
        requirement_id: str,
        radius_km: Optional[float] = 200.0,
        limit: int = 20,
    ) -> List[ProduceListing]:
        req = db.query(BuyerRequirement).filter(BuyerRequirement.id == requirement_id).first()
        if not req:
            raise NotFoundException(f"Buyer requirement '{requirement_id}' not found")

        query = (
            db.query(ProduceListing)
            .options(joinedload(ProduceListing.crop))
            .filter(
                ProduceListing.status == ListingStatus.ACTIVE,
                ProduceListing.crop_id == req.crop_id,
                ProduceListing.expected_price <= req.target_price,
            )
        )

        if req.variety:
            query = query.filter(
                (ProduceListing.variety == None) | (ProduceListing.variety.ilike(f"%{req.variety}%"))
            )

        if req.quality_grade:
            query = query.filter(ProduceListing.quality_grade == req.quality_grade)

        # Spatial filter if coordinates are available
        if radius_km and req.latitude is not None and req.longitude is not None:
            is_pg = db.bind.dialect.name == "postgresql"
            query = geo_service.apply_radius_filter(
                query, ProduceListing, req.latitude, req.longitude, radius_km, is_postgresql=is_pg
            )

        # Order by price ascending (best deal for buyer)
        return query.order_by(ProduceListing.expected_price.asc()).limit(limit).all()

    @staticmethod
    def match_requirements_for_listing(
        db: Session,
        listing_id: str,
        radius_km: Optional[float] = 200.0,
        limit: int = 20,
    ) -> List[BuyerRequirement]:
        listing = db.query(ProduceListing).filter(ProduceListing.id == listing_id).first()
        if not listing:
            raise NotFoundException(f"Produce listing '{listing_id}' not found")

        # Buyers whose target price >= listing's min_price or expected_price
        min_acceptable = listing.min_price or listing.expected_price
        query = (
            db.query(BuyerRequirement)
            .options(joinedload(BuyerRequirement.crop))
            .filter(
                BuyerRequirement.status == RequirementStatus.ACTIVE,
                BuyerRequirement.crop_id == listing.crop_id,
                BuyerRequirement.target_price >= min_acceptable,
            )
        )

        if listing.variety:
            query = query.filter(
                (BuyerRequirement.variety == None) | (BuyerRequirement.variety.ilike(f"%{listing.variety}%"))
            )

        # Spatial filter if coordinates are available
        if radius_km and listing.latitude is not None and listing.longitude is not None:
            is_pg = db.bind.dialect.name == "postgresql"
            query = geo_service.apply_radius_filter(
                query, BuyerRequirement, listing.latitude, listing.longitude, radius_km, is_postgresql=is_pg
            )

        # Order by target_price descending (highest price offer for seller)
        return query.order_by(BuyerRequirement.target_price.desc()).limit(limit).all()


marketplace_service = MarketplaceService()

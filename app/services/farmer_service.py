from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.farmer import FarmerProfile
from app.models.fpo import FPOProfile
from app.models.buyer import BuyerProfile
from app.schemas.farmer import FarmerProfileUpdate
from app.services.geo_service import geo_service


class FarmerService:
    @staticmethod
    def get_profile_by_user_id(db: Session, user_id: str) -> FarmerProfile:
        profile = db.query(FarmerProfile).filter(FarmerProfile.user_id == user_id).first()
        if not profile:
            raise NotFoundException("Farmer profile not found")
        return profile

    @staticmethod
    def get_farmer_by_id(db: Session, farmer_id: str) -> FarmerProfile:
        farmer = db.query(FarmerProfile).filter(FarmerProfile.id == farmer_id).first()
        if not farmer:
            raise NotFoundException("Farmer not found")
        return farmer

    @staticmethod
    def update_profile(db: Session, profile: FarmerProfile, data: FarmerProfileUpdate) -> FarmerProfile:
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(profile, key, value)

        # Update PostGIS point if latitude or longitude changed
        if "latitude" in update_dict or "longitude" in update_dict:
            profile.location = geo_service.create_point_wkt(profile.latitude, profile.longitude)

        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_relevant_fpos(db: Session, profile: FarmerProfile, radius_km: float = 50.0) -> List[FPOProfile]:
        """Finds FPOs in the vicinity or same district."""
        query = db.query(FPOProfile)
        is_pg = db.bind.dialect.name == "postgresql"
        if profile.latitude is not None and profile.longitude is not None:
            query = geo_service.apply_radius_filter(
                query, FPOProfile, profile.latitude, profile.longitude, radius_km, is_postgresql=is_pg
            )
        elif profile.district:
            query = query.filter(FPOProfile.district.ilike(profile.district))
        return query.limit(50).all()

    @staticmethod
    def get_relevant_buyers(db: Session, profile: FarmerProfile, radius_km: float = 100.0) -> List[BuyerProfile]:
        """Finds active buyers within distance radius or location area."""
        query = db.query(BuyerProfile)
        is_pg = db.bind.dialect.name == "postgresql"
        if profile.latitude is not None and profile.longitude is not None:
            query = geo_service.apply_radius_filter(
                query, BuyerProfile, profile.latitude, profile.longitude, radius_km, is_postgresql=is_pg
            )
        elif profile.district:
            query = query.filter(BuyerProfile.address.ilike(f"%{profile.district}%"))
        return query.limit(50).all()


farmer_service = FarmerService()

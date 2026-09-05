from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.buyer import BuyerProfile
from app.schemas.buyer import BuyerProfileUpdate
from app.services.geo_service import geo_service


class BuyerService:
    @staticmethod
    def get_profile_by_user_id(db: Session, user_id: str) -> BuyerProfile:
        profile = db.query(BuyerProfile).filter(BuyerProfile.user_id == user_id).first()
        if not profile:
            raise NotFoundException("Buyer profile not found")
        return profile

    @staticmethod
    def get_buyer_by_id(db: Session, buyer_id: str) -> BuyerProfile:
        buyer = db.query(BuyerProfile).filter(BuyerProfile.id == buyer_id).first()
        if not buyer:
            raise NotFoundException("Buyer not found")
        return buyer

    @staticmethod
    def update_profile(db: Session, profile: BuyerProfile, data: BuyerProfileUpdate) -> BuyerProfile:
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(profile, key, value)

        if "latitude" in update_dict or "longitude" in update_dict:
            profile.location = geo_service.create_point_wkt(profile.latitude, profile.longitude)

        db.commit()
        db.refresh(profile)
        return profile


buyer_service = BuyerService()

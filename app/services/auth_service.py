from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.user import User
from app.models.farmer import FarmerProfile
from app.models.fpo import FPOProfile
from app.models.buyer import BuyerProfile
from app.schemas.auth import RegisterProfileRequest
from app.services.geo_service import geo_service
from app.utils.enums import BuyerType, UserRole, VerificationStatus


class AuthService:
    @staticmethod
    def get_user_by_auth_id(db: Session, auth_user_id: str) -> Optional[User]:
        return db.query(User).filter(User.auth_user_id == auth_user_id).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def register_user_profile(
        db: Session,
        auth_user_id: str,
        token_email: Optional[str],
        token_phone: Optional[str],
        req: RegisterProfileRequest
    ) -> User:
        existing = db.query(User).filter(User.auth_user_id == auth_user_id).first()
        if existing:
            raise ConflictException("A profile for this authenticated account already exists.")

        user = User(
            auth_user_id=auth_user_id,
            role=req.role,
            email=token_email or req.email if hasattr(req, "email") else token_email,
            phone=token_phone or req.phone,
            is_active=True,
        )
        db.add(user)
        db.flush()

        location_geom = geo_service.create_point_wkt(req.latitude, req.longitude)

        if req.role == UserRole.FARMER:
            if not req.name:
                raise BadRequestException("Farmer name is required to complete profile registration.")
            farmer = FarmerProfile(
                user_id=user.id,
                name=req.name,
                phone=user.phone,
                address=req.address,
                village=req.village,
                district=req.district,
                state=req.state,
                pincode=req.pincode,
                latitude=req.latitude,
                longitude=req.longitude,
                location=location_geom,
                farm_size=req.farm_size,
                preferred_crops=[],
                verification_status=VerificationStatus.PENDING,
            )
            db.add(farmer)

        elif req.role == UserRole.FPO:
            if not req.organization_name or not req.registration_number or not req.contact_person:
                raise BadRequestException("FPO organization name, registration number, and contact person are required.")
            
            # Check unique registration number
            existing_fpo = db.query(FPOProfile).filter(FPOProfile.registration_number == req.registration_number).first()
            if existing_fpo:
                raise ConflictException("An FPO with this registration number already exists.")

            fpo = FPOProfile(
                user_id=user.id,
                organization_name=req.organization_name,
                registration_number=req.registration_number,
                contact_person=req.contact_person,
                phone=user.phone or req.phone or "",
                email=user.email,
                address=req.address,
                village_or_city=req.village,
                district=req.district,
                state=req.state,
                pincode=req.pincode,
                latitude=req.latitude,
                longitude=req.longitude,
                location=location_geom,
                description=req.business_description,
                verification_status=VerificationStatus.PENDING,
            )
            db.add(fpo)

        elif req.role == UserRole.BUYER:
            if not req.organization_name or not req.contact_person:
                raise BadRequestException("Buyer organization name and contact person are required.")

            buyer_type = BuyerType.WHOLESALER
            if req.buyer_type:
                try:
                    buyer_type = BuyerType(req.buyer_type)
                except ValueError:
                    buyer_type = BuyerType.WHOLESALER

            buyer = BuyerProfile(
                user_id=user.id,
                organization_name=req.organization_name,
                buyer_type=buyer_type,
                contact_person=req.contact_person,
                phone=user.phone or req.phone or "",
                email=user.email,
                address=req.address,
                location_name=req.village,
                latitude=req.latitude,
                longitude=req.longitude,
                location=location_geom,
                business_description=req.business_description,
                verification_status=VerificationStatus.PENDING,
            )
            db.add(buyer)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_full_profile(db: Session, user: User) -> Dict[str, Any]:
        profile_data = None
        if user.role == UserRole.FARMER and user.farmer_profile:
            fp = user.farmer_profile
            profile_data = {
                "id": fp.id,
                "name": fp.name,
                "phone": fp.phone,
                "address": fp.address,
                "village": fp.village,
                "district": fp.district,
                "state": fp.state,
                "pincode": fp.pincode,
                "latitude": fp.latitude,
                "longitude": fp.longitude,
                "farm_size": fp.farm_size,
                "preferred_crops": fp.preferred_crops,
                "verification_status": fp.verification_status,
                "created_at": fp.created_at,
                "updated_at": fp.updated_at,
            }
        elif user.role == UserRole.FPO and user.fpo_profile:
            fp = user.fpo_profile
            profile_data = {
                "id": fp.id,
                "organization_name": fp.organization_name,
                "registration_number": fp.registration_number,
                "contact_person": fp.contact_person,
                "phone": fp.phone,
                "email": fp.email,
                "address": fp.address,
                "village_or_city": fp.village_or_city,
                "district": fp.district,
                "state": fp.state,
                "pincode": fp.pincode,
                "latitude": fp.latitude,
                "longitude": fp.longitude,
                "description": fp.description,
                "verification_status": fp.verification_status,
                "created_at": fp.created_at,
                "updated_at": fp.updated_at,
            }
        elif user.role == UserRole.BUYER and user.buyer_profile:
            bp = user.buyer_profile
            profile_data = {
                "id": bp.id,
                "organization_name": bp.organization_name,
                "buyer_type": bp.buyer_type,
                "contact_person": bp.contact_person,
                "phone": bp.phone,
                "email": bp.email,
                "address": bp.address,
                "location_name": bp.location_name,
                "latitude": bp.latitude,
                "longitude": bp.longitude,
                "business_description": bp.business_description,
                "verification_status": bp.verification_status,
                "created_at": bp.created_at,
                "updated_at": bp.updated_at,
            }

        return {
            "id": user.id,
            "auth_user_id": user.auth_user_id,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "is_active": user.is_active,
            "profile": profile_data,
        }


auth_service = AuthService()

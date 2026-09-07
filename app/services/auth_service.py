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

        # Apply Maharashtra default geographic location for all users except admin if omitted
        lat = req.latitude if req.latitude is not None else (18.5204 if req.role != UserRole.ADMIN else None)
        lon = req.longitude if req.longitude is not None else (73.8567 if req.role != UserRole.ADMIN else None)
        state_val = req.state or ("Maharashtra" if req.role != UserRole.ADMIN else None)
        district_val = req.district or ("Pune" if req.role != UserRole.ADMIN else None)

        location_geom = geo_service.create_point_wkt(lat, lon) if (lat is not None and lon is not None) else None

        if req.role == UserRole.FARMER:
            name_val = req.name or "Maharashtra Farmer"
            farmer = FarmerProfile(
                user_id=user.id,
                name=name_val,
                phone=user.phone,
                address=req.address,
                village=req.village or "Pune Village",
                district=district_val,
                state=state_val,
                pincode=req.pincode or "411001",
                latitude=lat,
                longitude=lon,
                location=location_geom,
                farm_size=req.farm_size or 5.0,
                preferred_crops=[],
                verification_status=VerificationStatus.PENDING,
            )
            db.add(farmer)

        elif req.role == UserRole.FPO:
            org_name = req.organization_name or "Maharashtra Agro FPO"
            reg_num = req.registration_number or f"FPO-MH-{user.id[:8]}"
            contact = req.contact_person or "FPO Director"
            
            fpo = FPOProfile(
                user_id=user.id,
                organization_name=org_name,
                registration_number=reg_num,
                contact_person=contact,
                phone=user.phone or req.phone or "9876543210",
                email=user.email,
                address=req.address,
                village_or_city=req.village or "Nashik",
                district=district_val,
                state=state_val,
                pincode=req.pincode or "422001",
                latitude=lat,
                longitude=lon,
                location=location_geom,
                description=req.business_description or "Maharashtra Farmers Producer Organization",
                verification_status=VerificationStatus.PENDING,
            )
            db.add(fpo)

        elif req.role == UserRole.BUYER:
            org_name = req.organization_name or "Maharashtra Agri Traders"
            contact = req.contact_person or "Procurement Manager"

            buyer_type = BuyerType.WHOLESALER
            if req.buyer_type:
                try:
                    buyer_type = BuyerType(req.buyer_type)
                except ValueError:
                    buyer_type = BuyerType.WHOLESALER

            buyer = BuyerProfile(
                user_id=user.id,
                organization_name=org_name,
                buyer_type=buyer_type,
                contact_person=contact,
                phone=user.phone or req.phone or "9876543210",
                email=user.email,
                address=req.address,
                location_name=req.village or "Mumbai Mandi",
                district=district_val,
                state=state_val,
                latitude=lat,
                longitude=lon,
                location=location_geom,
                business_description=req.business_description or "Maharashtra Agri Buying Enterprise",
                verification_status=VerificationStatus.PENDING,
            )
            db.add(buyer)

        elif req.role in (UserRole.STORAGE, UserRole.TRANSPORT, UserRole.QUALITY):
            # General service provider profile represented as Buyer/FPO compatible profile if specific profile table is uninstantiated
            org_name = req.organization_name or f"Maharashtra {req.role.value.capitalize()} Service"
            contact = req.contact_person or f"{req.role.value.capitalize()} Service Manager"
            buyer = BuyerProfile(
                user_id=user.id,
                organization_name=org_name,
                buyer_type=BuyerType.WHOLESALER,
                contact_person=contact,
                phone=user.phone or req.phone or "9876543210",
                email=user.email,
                address=req.address,
                location_name=req.village or "Maharashtra Hub",
                district=district_val,
                state=state_val,
                latitude=lat,
                longitude=lon,
                location=location_geom,
                business_description=req.business_description or f"Maharashtra {req.role.value.capitalize()} Service Provider",
                verification_status=VerificationStatus.PENDING,
            )
            db.add(buyer)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_user_role(db: Session, user: User, new_role: UserRole) -> User:
        """Updates the active user's role and ensures appropriate profile structure exists."""
        user.role = new_role

        if new_role == UserRole.FARMER and not user.farmer_profile:
            farmer = FarmerProfile(
                user_id=user.id,
                name="Farmer User",
                phone=user.phone or "9822012345",
                district="Pune",
                state="Maharashtra",
                verification_status=VerificationStatus.VERIFIED,
            )
            db.add(farmer)
        elif new_role == UserRole.FPO and not user.fpo_profile:
            fpo = FPOProfile(
                user_id=user.id,
                organization_name="FPO Organization",
                district="Nashik",
                state="Maharashtra",
                verification_status=VerificationStatus.VERIFIED,
            )
            db.add(fpo)
        elif new_role in (UserRole.BUYER, UserRole.STORAGE, UserRole.TRANSPORT, UserRole.QUALITY) and not user.buyer_profile:
            org_title = f"{new_role.value.capitalize()} Service Provider" if new_role != UserRole.BUYER else "Agri Buyer Enterprise"
            buyer = BuyerProfile(
                user_id=user.id,
                organization_name=org_title,
                buyer_type=BuyerType.WHOLESALER,
                district="Mumbai",
                state="Maharashtra",
                verification_status=VerificationStatus.VERIFIED,
            )
            db.add(buyer)

        db.add(user)
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
                "district": fp.district or "Pune",
                "state": fp.state or "Maharashtra",
                "pincode": fp.pincode,
                "latitude": fp.latitude or 18.5204,
                "longitude": fp.longitude or 73.8567,
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
                "district": fp.district or "Nashik",
                "state": fp.state or "Maharashtra",
                "pincode": fp.pincode,
                "latitude": fp.latitude or 19.9975,
                "longitude": fp.longitude or 73.7898,
                "description": fp.description,
                "verification_status": fp.verification_status,
                "created_at": fp.created_at,
                "updated_at": fp.updated_at,
            }
        elif user.role in (UserRole.BUYER, UserRole.STORAGE, UserRole.TRANSPORT, UserRole.QUALITY) and user.buyer_profile:
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
                "district": getattr(bp, "district", "Mumbai"),
                "state": getattr(bp, "state", "Maharashtra"),
                "latitude": bp.latitude or 19.0760,
                "longitude": bp.longitude or 72.8777,
                "business_description": bp.business_description,
                "verification_status": bp.verification_status,
                "created_at": bp.created_at,
                "updated_at": bp.updated_at,
            }
        elif user.role == UserRole.ADMIN:
            profile_data = {
                "name": "System Administrator",
                "role": "ADMIN",
                "district": None,
                "state": None,
                "latitude": None,
                "longitude": None,
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

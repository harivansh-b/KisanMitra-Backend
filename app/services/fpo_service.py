from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.farmer import FarmerProfile
from app.models.fpo import FPOProfile
from app.models.fpo_member import FPOMember
from app.schemas.fpo import FPOMemberAddRequest, FPOMemberUpdate, FPOProfileUpdate
from app.services.geo_service import geo_service
from app.utils.enums import FPOMemberStatus


class FPOService:
    @staticmethod
    def get_profile_by_user_id(db: Session, user_id: str) -> FPOProfile:
        profile = db.query(FPOProfile).filter(FPOProfile.user_id == user_id).first()
        if not profile:
            raise NotFoundException("FPO profile not found")
        return profile

    @staticmethod
    def get_fpo_by_id(db: Session, fpo_id: str) -> FPOProfile:
        fpo = db.query(FPOProfile).filter(FPOProfile.id == fpo_id).first()
        if not fpo:
            raise NotFoundException("FPO not found")
        return fpo

    @staticmethod
    def update_profile(db: Session, profile: FPOProfile, data: FPOProfileUpdate) -> FPOProfile:
        update_dict = data.model_dump(exclude_unset=True)
        if "registration_number" in update_dict and update_dict["registration_number"] != profile.registration_number:
            existing = (
                db.query(FPOProfile)
                .filter(
                    FPOProfile.registration_number == update_dict["registration_number"],
                    FPOProfile.id != profile.id,
                )
                .first()
            )
            if existing:
                raise ConflictException("An FPO with this registration number already exists.")

        for key, value in update_dict.items():
            setattr(profile, key, value)

        if "latitude" in update_dict or "longitude" in update_dict:
            profile.location = geo_service.create_point_wkt(profile.latitude, profile.longitude)

        db.commit()
        db.refresh(profile)
        return profile

    # Membership Management
    @staticmethod
    def add_member(db: Session, fpo: FPOProfile, req: FPOMemberAddRequest) -> FPOMember:
        # Verify farmer exists
        farmer = db.query(FarmerProfile).filter(FarmerProfile.id == req.farmer_id).first()
        if not farmer:
            raise NotFoundException(f"Farmer profile with ID '{req.farmer_id}' not found.")

        # Check existing membership
        existing = (
            db.query(FPOMember)
            .filter(FPOMember.fpo_id == fpo.id, FPOMember.farmer_id == req.farmer_id)
            .first()
        )
        if existing:
            if existing.status == FPOMemberStatus.ACTIVE:
                raise ConflictException("This farmer is already an active member of this FPO.")
            else:
                existing.status = FPOMemberStatus.ACTIVE
                existing.membership_role = req.membership_role
                db.commit()
                db.refresh(existing)
                return existing

        member = FPOMember(
            fpo_id=fpo.id,
            farmer_id=req.farmer_id,
            membership_role=req.membership_role,
            status=FPOMemberStatus.ACTIVE,
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def remove_member(db: Session, fpo: FPOProfile, farmer_id: str) -> None:
        member = (
            db.query(FPOMember)
            .filter(FPOMember.fpo_id == fpo.id, FPOMember.farmer_id == farmer_id)
            .first()
        )
        if not member:
            raise NotFoundException(f"Farmer membership not found in this FPO.")
        db.delete(member)
        db.commit()

    @staticmethod
    def update_member(db: Session, fpo: FPOProfile, farmer_id: str, data: FPOMemberUpdate) -> FPOMember:
        member = (
            db.query(FPOMember)
            .filter(FPOMember.fpo_id == fpo.id, FPOMember.farmer_id == farmer_id)
            .first()
        )
        if not member:
            raise NotFoundException(f"Farmer membership not found in this FPO.")

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(member, key, value)

        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def list_members(db: Session, fpo: FPOProfile, offset: int = 0, limit: int = 20) -> Tuple[List[FPOMember], int]:
        query = (
            db.query(FPOMember)
            .options(joinedload(FPOMember.farmer))
            .filter(FPOMember.fpo_id == fpo.id)
        )
        total = query.count()
        members = query.offset(offset).limit(limit).all()
        return members, total


fpo_service = FPOService()

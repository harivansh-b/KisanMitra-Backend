from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.buyer_requirement import BuyerRequirement
from app.models.crop import Crop
from app.models.user import User
from app.schemas.requirement import BuyerRequirementCreate, BuyerRequirementFilter, BuyerRequirementUpdate
from app.services.geo_service import geo_service
from app.utils.enums import RequirementStatus, UserRole


class RequirementService:
    @staticmethod
    def get_requirement_by_id(db: Session, req_id: str) -> BuyerRequirement:
        requirement = (
            db.query(BuyerRequirement)
            .options(joinedload(BuyerRequirement.crop))
            .filter(BuyerRequirement.id == req_id)
            .first()
        )
        if not requirement:
            raise NotFoundException(f"Buyer requirement with ID '{req_id}' not found")
        return requirement

    @staticmethod
    def create_requirement(db: Session, user: User, data: BuyerRequirementCreate) -> BuyerRequirement:
        if user.role != UserRole.BUYER and user.role != UserRole.ADMIN:
            raise ForbiddenException("Only registered Buyers can post sourcing requirements.")

        crop = db.query(Crop).filter(Crop.id == data.crop_id, Crop.is_active == True).first()
        if not crop:
            raise NotFoundException(f"Active crop with ID '{data.crop_id}' not found.")

        location_geom = geo_service.create_point_wkt(data.latitude, data.longitude)

        req = BuyerRequirement(
            buyer_id=user.id,
            crop_id=data.crop_id,
            variety=data.variety,
            required_quantity=data.required_quantity,
            unit=data.unit,
            quality_grade=data.quality_grade,
            target_price=data.target_price,
            delivery_location=data.delivery_location,
            latitude=data.latitude,
            longitude=data.longitude,
            location=location_geom,
            required_from=data.required_from,
            required_until=data.required_until,
            description=data.description,
            status=RequirementStatus.ACTIVE,
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def update_requirement(
        db: Session, req_id: str, user: User, data: BuyerRequirementUpdate
    ) -> BuyerRequirement:
        req = RequirementService.get_requirement_by_id(db, req_id)
        if req.buyer_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenException("You do not have permission to modify this requirement.")

        update_dict = data.model_dump(exclude_unset=True)

        if "crop_id" in update_dict and update_dict["crop_id"] != req.crop_id:
            crop = db.query(Crop).filter(Crop.id == update_dict["crop_id"], Crop.is_active == True).first()
            if not crop:
                raise NotFoundException(f"Active crop with ID '{update_dict['crop_id']}' not found.")

        for key, value in update_dict.items():
            setattr(req, key, value)

        if "latitude" in update_dict or "longitude" in update_dict:
            req.location = geo_service.create_point_wkt(req.latitude, req.longitude)

        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def cancel_requirement(db: Session, req_id: str, user: User) -> BuyerRequirement:
        req = RequirementService.get_requirement_by_id(db, req_id)
        if req.buyer_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenException("You do not have permission to cancel this requirement.")

        req.status = RequirementStatus.CANCELLED
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def list_requirements(
        db: Session,
        filters: BuyerRequirementFilter,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[BuyerRequirement], int]:
        query = db.query(BuyerRequirement).options(joinedload(BuyerRequirement.crop))

        if filters.status:
            query = query.filter(BuyerRequirement.status == filters.status)
        if filters.crop_id:
            query = query.filter(BuyerRequirement.crop_id == filters.crop_id)
        if filters.variety:
            query = query.filter(BuyerRequirement.variety.ilike(f"%{filters.variety}%"))
        if filters.quality_grade:
            query = query.filter(BuyerRequirement.quality_grade == filters.quality_grade)
        if filters.min_price is not None:
            query = query.filter(BuyerRequirement.target_price >= filters.min_price)
        if filters.max_price is not None:
            query = query.filter(BuyerRequirement.target_price <= filters.max_price)
        if filters.min_quantity is not None:
            query = query.filter(BuyerRequirement.required_quantity >= filters.min_quantity)
        if filters.max_quantity is not None:
            query = query.filter(BuyerRequirement.required_quantity <= filters.max_quantity)

        # PostGIS radius filter
        if filters.latitude is not None and filters.longitude is not None and filters.radius_km:
            is_pg = db.bind.dialect.name == "postgresql"
            query = geo_service.apply_radius_filter(
                query, BuyerRequirement, filters.latitude, filters.longitude, filters.radius_km, is_postgresql=is_pg
            )

        total = query.count()
        requirements = query.order_by(BuyerRequirement.created_at.desc()).offset(offset).limit(limit).all()
        return requirements, total

    @staticmethod
    def list_buyer_requirements(
        db: Session,
        buyer_id: str,
        offset: int = 0,
        limit: int = 20,
        status: Optional[RequirementStatus] = None,
    ) -> Tuple[List[BuyerRequirement], int]:
        query = (
            db.query(BuyerRequirement)
            .options(joinedload(BuyerRequirement.crop))
            .filter(BuyerRequirement.buyer_id == buyer_id)
        )
        if status:
            query = query.filter(BuyerRequirement.status == status)

        total = query.count()
        requirements = query.order_by(BuyerRequirement.created_at.desc()).offset(offset).limit(limit).all()
        return requirements, total


requirement_service = RequirementService()

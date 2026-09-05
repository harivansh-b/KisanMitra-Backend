from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.models.crop import Crop
from app.schemas.crop import CropCreate, CropUpdate
from app.utils.enums import UnitEnum


class CropService:
    @staticmethod
    def get_crop_by_id(db: Session, crop_id: str) -> Crop:
        crop = db.query(Crop).filter(Crop.id == crop_id).first()
        if not crop:
            raise NotFoundException(f"Crop with ID '{crop_id}' not found")
        return crop

    @staticmethod
    def list_crops(
        db: Session,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = True,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Crop], int]:
        query = db.query(Crop)
        if category:
            query = query.filter(Crop.category.ilike(f"%{category}%"))
        if search:
            query = query.filter(
                (Crop.name.ilike(f"%{search}%")) | (Crop.local_name.ilike(f"%{search}%"))
            )
        if is_active is not None:
            query = query.filter(Crop.is_active == is_active)

        total = query.count()
        crops = query.order_by(Crop.name.asc()).offset(offset).limit(limit).all()
        return crops, total

    @staticmethod
    def create_crop(db: Session, data: CropCreate) -> Crop:
        existing = db.query(Crop).filter(Crop.name.ilike(data.name)).first()
        if existing:
            raise ConflictException(f"Crop with name '{data.name}' already exists.")

        crop = Crop(**data.model_dump())
        db.add(crop)
        db.commit()
        db.refresh(crop)
        return crop

    @staticmethod
    def update_crop(db: Session, crop_id: str, data: CropUpdate) -> Crop:
        crop = CropService.get_crop_by_id(db, crop_id)
        update_dict = data.model_dump(exclude_unset=True)
        if "name" in update_dict and update_dict["name"].lower() != crop.name.lower():
            existing = db.query(Crop).filter(Crop.name.ilike(update_dict["name"]), Crop.id != crop.id).first()
            if existing:
                raise ConflictException(f"Crop with name '{update_dict['name']}' already exists.")

        for key, value in update_dict.items():
            setattr(crop, key, value)

        db.commit()
        db.refresh(crop)
        return crop

    @staticmethod
    def seed_default_crops(db: Session) -> int:
        """Seeds common Indian crops if the table is empty."""
        count = db.query(Crop).count()
        if count > 0:
            return 0

        default_crops = [
            {"name": "Wheat", "local_name": "Gehun (गेहूं)", "category": "CEREALS", "variety": "Sharbati", "default_unit": UnitEnum.QUINTAL},
            {"name": "Paddy / Rice", "local_name": "Dhan / Chawal (धान/चावल)", "category": "CEREALS", "variety": "Basmati 1121", "default_unit": UnitEnum.QUINTAL},
            {"name": "Maize", "local_name": "Makka (मक्का)", "category": "CEREALS", "variety": "Yellow Hybrid", "default_unit": UnitEnum.QUINTAL},
            {"name": "Soybean", "local_name": "Soyabean (सोयाबीन)", "category": "OILSEEDS", "variety": "JS 335", "default_unit": UnitEnum.QUINTAL},
            {"name": "Mustard", "local_name": "Sarson (सरसों)", "category": "OILSEEDS", "variety": "Pusa Bold", "default_unit": UnitEnum.QUINTAL},
            {"name": "Cotton", "local_name": "Kapas (कपास)", "category": "FIBER", "variety": "Bt Cotton", "default_unit": UnitEnum.QUINTAL},
            {"name": "Onion", "local_name": "Pyaz (प्याज)", "category": "VEGETABLES", "variety": "Nashik Red", "default_unit": UnitEnum.QUINTAL},
            {"name": "Potato", "local_name": "Aloo (आलू)", "category": "VEGETABLES", "variety": "Kufri Jyoti", "default_unit": UnitEnum.QUINTAL},
            {"name": "Tomato", "local_name": "Tamatar (टमाटर)", "category": "VEGETABLES", "variety": "Hybrid Red", "default_unit": UnitEnum.QUINTAL},
            {"name": "Gram / Chickpea", "local_name": "Chana (चना)", "category": "PULSES", "variety": "Desi Chana", "default_unit": UnitEnum.QUINTAL},
        ]

        for c_data in default_crops:
            crop = Crop(**c_data, is_active=True)
            db.add(crop)
        db.commit()
        return len(default_crops)


crop_service = CropService()
